## @file
# This file is used to the implementation of Bios layout handler.
#
# Copyright (c) 2021-, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
##
import os
from core.BiosTree import *
from core.GuidTools import GUIDTools
from core.BiosTreeNode import *
from FirmwareStorageFormat.Common import *
from utils.FmmtLogger import FmmtLogger as logger

EFI_FVB2_ERASE_POLARITY = 0x00000800

def ChangeSize(TargetTree, size_delta: int=0) -> None:
    # If Size increase delta, then should be: size_delta = -delta
    if type(TargetTree.Data.Header) == type(EFI_FFS_FILE_HEADER2()) or type(TargetTree.Data.Header) == type(EFI_COMMON_SECTION_HEADER2()):
        TargetTree.Data.Size -= size_delta
        TargetTree.Data.Header.ExtendedSize -= size_delta
    elif TargetTree.type == SECTION_TREE and TargetTree.Data.OriData:
        OriSize = TargetTree.Data.Header.SECTION_SIZE
        OriSize -= size_delta
        TargetTree.Data.Header.Size[0] = OriSize % (16**2)
        TargetTree.Data.Header.Size[1] = OriSize % (16**4) //(16**2)
        TargetTree.Data.Header.Size[2] = OriSize // (16**4)
    else:
        TargetTree.Data.Size -= size_delta
        TargetTree.Data.Header.Size[0] = TargetTree.Data.Size % (16**2)
        TargetTree.Data.Header.Size[1] = TargetTree.Data.Size % (16**4) //(16**2)
        TargetTree.Data.Header.Size[2] = TargetTree.Data.Size // (16**4)

def ModifyFfsType(TargetFfs) -> None:
    if type(TargetFfs.Data.Header) == type(EFI_FFS_FILE_HEADER()) and TargetFfs.Data.Size > 0xFFFFFF:
        ExtendSize = TargetFfs.Data.Header.FFS_FILE_SIZE + 8
        New_Header = EFI_FFS_FILE_HEADER2()
        New_Header.Name = TargetFfs.Data.Header.Name
        New_Header.IntegrityCheck = TargetFfs.Data.Header.IntegrityCheck
        New_Header.Type = TargetFfs.Data.Header.Type
        New_Header.Attributes = TargetFfs.Data.Header.Attributes | 0x01  # set the Attribute with FFS_ATTRIB_LARGE_FILE (0x01)
        NewSize = 0
        New_Header.Size[0] = NewSize % (16**2)    # minus the delta size of Header
        New_Header.Size[1] = NewSize % (16**4) //(16**2)
        New_Header.Size[2] = NewSize // (16**4)
        New_Header.State = TargetFfs.Data.Header.State
        New_Header.ExtendedSize = ExtendSize
        TargetFfs.Data.Header = New_Header
        TargetFfs.Data.Size = TargetFfs.Data.Header.FFS_FILE_SIZE
        TargetFfs.Data.HeaderLength = TargetFfs.Data.Header.HeaderLength
        TargetFfs.Data.ModCheckSum()
    elif type(TargetFfs.Data.Header) == type(EFI_FFS_FILE_HEADER2()) and TargetFfs.Data.Size <= 0xFFFFFF:
        New_Header = EFI_FFS_FILE_HEADER()
        New_Header.Name = TargetFfs.Data.Header.Name
        New_Header.IntegrityCheck = TargetFfs.Data.Header.IntegrityCheck
        New_Header.Type = TargetFfs.Data.Header.Type
        New_Header.Attributes = TargetFfs.Data.Header.Attributes - 1  # remove the FFS_ATTRIB_LARGE_FILE (0x01) from Attribute
        New_Header.Size[0] = (TargetFfs.Data.Size - 8) % (16**2)    # minus the delta size of Header
        New_Header.Size[1] = (TargetFfs.Data.Size - 8) % (16**4) //(16**2)
        New_Header.Size[2] = (TargetFfs.Data.Size - 8) // (16**4)
        New_Header.State = TargetFfs.Data.Header.State
        TargetFfs.Data.Header = New_Header
        TargetFfs.Data.Size = TargetFfs.Data.Header.FFS_FILE_SIZE
        TargetFfs.Data.HeaderLength = TargetFfs.Data.Header.HeaderLength
        TargetFfs.Data.ModCheckSum()
        if struct2stream(TargetFfs.Parent.Data.Header.FileSystemGuid) == EFI_FIRMWARE_FILE_SYSTEM3_GUID_BYTE:
            NeedChange = True
            for item in TargetFfs.Parent.Child:
                if type(item.Data.Header) == type(EFI_FFS_FILE_HEADER2()):
                    NeedChange = False
            if NeedChange:
                TargetFfs.Parent.Data.Header.FileSystemGuid = ModifyGuidFormat("8c8ce578-8a3d-4f1c-9935-896185c32dd3")

    if type(TargetFfs.Data.Header) == type(EFI_FFS_FILE_HEADER2()):
        TarParent = TargetFfs.Parent
        while TarParent:
            if TarParent.type == FV_TREE and struct2stream(TarParent.Data.Header.FileSystemGuid) == EFI_FIRMWARE_FILE_SYSTEM2_GUID_BYTE:
                TarParent.Data.Header.FileSystemGuid = ModifyGuidFormat("5473C07A-3DCB-4dca-BD6F-1E9689E7349A")
            TarParent = TarParent.Parent

def PadSectionModify(PadSection, Offset) -> None:
    # Offset > 0, Size decrease; Offset < 0, Size increase;
    ChangeSize(PadSection, Offset)
    PadSection.Data.Data = (PadSection.Data.Size - PadSection.Data.HeaderLength) * b'\xff'

def ModifySectionType(TargetSection) -> None:
    # If Section Size is increased larger than 0xFFFFFF, need modify Section Header from EFI_COMMON_SECTION_HEADER to EFI_COMMON_SECTION_HEADER2.
    if type(TargetSection.Data.Header) == type(EFI_COMMON_SECTION_HEADER()) and TargetSection.Data.Size >= 0xFFFFFF:
        New_Header = EFI_COMMON_SECTION_HEADER2()
        New_Header.Type = TargetSection.Data.Header.Type
        NewSize = 0xFFFFFF
        New_Header.Size[0] = NewSize % (16**2)    # minus the delta size of Header
        New_Header.Size[1] = NewSize % (16**4) //(16**2)
        New_Header.Size[2] = NewSize // (16**4)
        New_Header.ExtendedSize = TargetSection.Data.Size + 4
        TargetSection.Data.Header = New_Header
        TargetSection.Data.Size = TargetSection.Data.Header.SECTION_SIZE
        # Align the Header's added 4 bit to 8-alignment to promise the following Ffs's align correctly.
        if TargetSection.LastRel.Data.IsPadSection:
            PadSectionModify(TargetSection.LastRel, -4)
        else:
            SecParent = TargetSection.Parent
            Target_index = SecParent.Child.index(TargetSection)
            NewPadSection = SectionNode(b'\x00\x00\x00\x19')
            SecParent.insertChild(NewPadSection, Target_index)
    # If Section Size is decreased smaller than 0xFFFFFF, need modify Section Header from EFI_COMMON_SECTION_HEADER2 to EFI_COMMON_SECTION_HEADER.
    elif type(TargetSection.Data.Header) == type(EFI_COMMON_SECTION_HEADER2()) and TargetSection.Data.Size < 0xFFFFFF:
        New_Header = EFI_COMMON_SECTION_HEADER()
        New_Header.Type = TargetSection.Data.Header.Type
        New_Header.Size[0] = (TargetSection.Data.Size - 4) % (16**2)    # minus the delta size of Header
        New_Header.Size[1] = (TargetSection.Data.Size - 4) % (16**4) //(16**2)
        New_Header.Size[2] = (TargetSection.Data.Size - 4) // (16**4)
        TargetSection.Data.Header = New_Header
        TargetSection.Data.Size = TargetSection.Data.Header.SECTION_SIZE
        # Align the Header's added 4 bit to 8-alignment to promise the following Ffs's align correctly.
        if TargetSection.LastRel.Data.IsPadSection:
            PadSectionModify(TargetSection.LastRel, -4)
        else:
            SecParent = TargetSection.Parent
            Target_index = SecParent.Child.index(TargetSection)
            NewPadSection = SectionNode(b'\x00\x00\x00\x19')
            SecParent.insertChild(NewPadSection, Target_index)

def ModifyFvExtData(TreeNode) -> None:
    FvExtData = b''
    if TreeNode.Data.Header.ExtHeaderOffset:
        FvExtHeader = struct2stream(TreeNode.Data.ExtHeader)
        FvExtData += FvExtHeader
    if TreeNode.Data.Header.ExtHeaderOffset and TreeNode.Data.ExtEntryExist:
        FvExtEntry = struct2stream(TreeNode.Data.ExtEntry)
        FvExtData += FvExtEntry
    if FvExtData:
        InfoNode = TreeNode.Child[0]
        InfoNode.Data.Data = FvExtData + InfoNode.Data.Data[TreeNode.Data.ExtHeader.ExtHeaderSize:]
        InfoNode.Data.ModCheckSum()

def ModifyFvSystemGuid(TargetFv) -> None:
    if struct2stream(TargetFv.Data.Header.FileSystemGuid) == EFI_FIRMWARE_FILE_SYSTEM2_GUID_BYTE:
        TargetFv.Data.Header.FileSystemGuid = ModifyGuidFormat("5473C07A-3DCB-4dca-BD6F-1E9689E7349A")
    TargetFv.Data.ModCheckSum()
    TargetFv.Data.Data = b''
    for item in TargetFv.Child:
        if item.type == FFS_FREE_SPACE:
            TargetFv.Data.Data += item.Data.Data + item.Data.PadData
        else:
            TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData

class FvHandler:
    def __init__(self, NewFfs, TargetFfs=None) -> None:
        self.NewFfs = NewFfs
        self.TargetFfs = TargetFfs
        self.Status = False
        self.Remain_New_Free_Space = 0
        self.TargetOrder = None

    ## Use for Compress the Section Data
    def CompressData(self, TargetTree) -> None:
        TreePath = TargetTree.GetTreePath()
        pos = len(TreePath)
        while pos:
            if not self.Status:
                if TreePath[pos-1].type == SECTION_TREE and TreePath[pos-1].Data.Type == 0x02:
                    self.CompressSectionData(TreePath[pos-1], None, TreePath[pos-1].Data.ExtHeader.SectionDefinitionGuid)
                else:
                    if pos == len(TreePath):
                        self.CompressSectionData(TreePath[pos-1], pos)
                    else:
                        self.CompressSectionData(TreePath[pos-1], None)
            pos -= 1

    def CompressSectionData(self, TargetTree, pos: int, GuidTool=None) -> None:
        NewData = b''
        temp_save_child = TargetTree.Child
        if TargetTree.Data:
            # Update current node data as adding all the header and data of its child node.
            for item in temp_save_child:
                if item.type == SECTION_TREE and not item.Data.OriData and item.Data.ExtHeader:
                    NewData += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.Data + item.Data.PadData
                elif item.type == SECTION_TREE and item.Data.OriData and not item.Data.ExtHeader:
                    NewData += struct2stream(item.Data.Header) + item.Data.OriData + item.Data.PadData
                elif item.type == SECTION_TREE and item.Data.OriData and item.Data.ExtHeader:
                    NewData += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.OriData + item.Data.PadData
                elif item.type == FFS_FREE_SPACE:
                    NewData += item.Data.Data + item.Data.PadData
                else:
                    NewData += struct2stream(item.Data.Header) + item.Data.Data + item.Data.PadData
            # If node is FFS_TREE, update Pad data and Header info.
            # Remain_New_Free_Space is used for move more free space into lst level Fv.
            if TargetTree.type == FFS_TREE:
                New_Pad_Size = GetPadSize(len(NewData), 8)
                Size_delta = len(NewData) - len(TargetTree.Data.Data)
                ChangeSize(TargetTree, -Size_delta)
                Delta_Pad_Size = len(TargetTree.Data.PadData) - New_Pad_Size
                self.Remain_New_Free_Space += Delta_Pad_Size
                TargetTree.Data.PadData = b'\xff' * New_Pad_Size
                TargetTree.Data.ModCheckSum()
            # If node is FV_TREE, update Pad data and Header info.
            # Consume Remain_New_Free_Space is used for move more free space into lst level Fv.
            elif TargetTree.type == FV_TREE or TargetTree.type == SEC_FV_TREE and not pos:
                if self.Remain_New_Free_Space:
                    if TargetTree.Data.Free_Space:
                        TargetTree.Data.Free_Space += self.Remain_New_Free_Space
                        NewData += self.Remain_New_Free_Space * b'\xff'
                        TargetTree.Child[-1].Data.Data += self.Remain_New_Free_Space * b'\xff'
                    else:
                        TargetTree.Data.Data += self.Remain_New_Free_Space * b'\xff'
                        New_Free_Space = BIOSTREE('FREE_SPACE')
                        New_Free_Space.type = FFS_FREE_SPACE
                        New_Free_Space.Data = FreeSpaceNode(b'\xff' * self.Remain_New_Free_Space)
                        TargetTree.insertChild(New_Free_Space)
                    self.Remain_New_Free_Space = 0
                if TargetTree.type == SEC_FV_TREE:
                    Size_delta = len(NewData) + self.Remain_New_Free_Space - len(TargetTree.Data.Data)
                    TargetTree.Data.Header.FvLength += Size_delta
                TargetTree.Data.ModFvExt()
                TargetTree.Data.ModFvSize()
                TargetTree.Data.ModExtHeaderData()
                ModifyFvExtData(TargetTree)
                TargetTree.Data.ModCheckSum()
            # If node is SECTION_TREE and not guided section, update Pad data and Header info.
            # Remain_New_Free_Space is used for move more free space into lst level Fv.
            elif TargetTree.type == SECTION_TREE and TargetTree.Data.Type != 0x02:
                New_Pad_Size = GetPadSize(len(NewData), 4)
                Size_delta = len(NewData) - len(TargetTree.Data.Data)
                ChangeSize(TargetTree, -Size_delta)
                if TargetTree.NextRel:
                    Delta_Pad_Size = len(TargetTree.Data.PadData) - New_Pad_Size
                    self.Remain_New_Free_Space += Delta_Pad_Size
                    TargetTree.Data.PadData = b'\x00' * New_Pad_Size
            TargetTree.Data.Data = NewData
        if GuidTool:
            guidtool = GUIDTools().__getitem__(struct2stream(GuidTool))
            if not guidtool.ifexist:
                logger.error("GuidTool {} is not found when decompressing {} file.\n".format(guidtool.command, TargetTree.Parent.Data.Name))
                raise Exception("Process Failed: GuidTool not found!")
            CompressedData = guidtool.pack(TargetTree.Data.Data)
            if len(CompressedData) < len(TargetTree.Data.OriData):
                New_Pad_Size = GetPadSize(len(CompressedData), SECTION_COMMON_ALIGNMENT)
                Size_delta = len(CompressedData) - len(TargetTree.Data.OriData)
                ChangeSize(TargetTree, -Size_delta)
                if TargetTree.NextRel:
                    TargetTree.Data.PadData = b'\x00' * New_Pad_Size
                    self.Remain_New_Free_Space = len(TargetTree.Data.OriData) + len(TargetTree.Data.PadData) - len(CompressedData) - New_Pad_Size
                else:
                    TargetTree.Data.PadData = b''
                    self.Remain_New_Free_Space = len(TargetTree.Data.OriData) - len(CompressedData)
                TargetTree.Data.OriData = CompressedData
            elif len(CompressedData) == len(TargetTree.Data.OriData):
                TargetTree.Data.OriData = CompressedData
            elif len(CompressedData) > len(TargetTree.Data.OriData):
                New_Pad_Size = GetPadSize(len(CompressedData), SECTION_COMMON_ALIGNMENT)
                self.Remain_New_Free_Space = len(CompressedData) + New_Pad_Size - len(TargetTree.Data.OriData) - len(TargetTree.Data.PadData)
                self.ModifyTest(TargetTree, self.Remain_New_Free_Space)
                self.Status = True

    def ModifyTest(self, ParTree, Needed_Space: int) -> None:
        # If have needed space, will find if there have free space in parent tree, meanwhile update the node data.
        if Needed_Space > 0:
            # If current node is a Fv node
            if ParTree.type == FV_TREE or ParTree.type == SEC_FV_TREE:
                ParTree.Data.Data = b''
                # First check if Fv free space is enough for needed space.
                # If so, use the current Fv free space;
                # Else, use all the Free space, and recalculate needed space, continue finding in its parent node.
                Needed_Space = Needed_Space - ParTree.Data.Free_Space
                if Needed_Space < 0:
                    ParTree.Child[-1].Data.Data = b'\xff' * (-Needed_Space)
                    ParTree.Data.Free_Space = (-Needed_Space)
                    self.Status = True
                else:
                    if ParTree.type == FV_TREE:
                        self.Status = False
                    else:
                        BlockSize = ParTree.Data.Header.BlockMap[0].Length
                        New_Add_Len = BlockSize - Needed_Space%BlockSize
                        if New_Add_Len % BlockSize:
                            ParTree.Child[-1].Data.Data = b'\xff' * New_Add_Len
                            ParTree.Data.Free_Space = New_Add_Len
                            Needed_Space += New_Add_Len
                        else:
                            ParTree.Child.remove(ParTree.Child[-1])
                            ParTree.Data.Free_Space = 0
                        ParTree.Data.Size += Needed_Space
                        ParTree.Data.Header.Fvlength = ParTree.Data.Size
                ModifyFvSystemGuid(ParTree)
                for item in ParTree.Child:
                    if item.type == FFS_FREE_SPACE:
                        ParTree.Data.Data += item.Data.Data + item.Data.PadData
                    else:
                        ParTree.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                ParTree.Data.ModFvExt()
                ParTree.Data.ModFvSize()
                ParTree.Data.ModExtHeaderData()
                ModifyFvExtData(ParTree)
                ParTree.Data.ModCheckSum()
            # If current node is a Ffs node
            elif ParTree.type == FFS_TREE:
                ParTree.Data.Data = b''
                OriHeaderLen = ParTree.Data.HeaderLength
                # Update its data as adding all the header and data of its child node.
                for item in ParTree.Child:
                    if item.Data.OriData:
                        if item.Data.ExtHeader:
                            ParTree.Data.Data += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.OriData + item.Data.PadData
                        else:
                            ParTree.Data.Data += struct2stream(item.Data.Header)+ item.Data.OriData + item.Data.PadData
                    else:
                        if item.Data.ExtHeader:
                            ParTree.Data.Data += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.Data + item.Data.PadData
                        else:
                            ParTree.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                ChangeSize(ParTree, -Needed_Space)
                ModifyFfsType(ParTree)
                # Recalculate pad data, update needed space with Delta_Pad_Size.
                Needed_Space += ParTree.Data.HeaderLength - OriHeaderLen
                New_Pad_Size = GetPadSize(ParTree.Data.Size, FFS_COMMON_ALIGNMENT)
                Delta_Pad_Size = New_Pad_Size - len(ParTree.Data.PadData)
                Needed_Space += Delta_Pad_Size
                ParTree.Data.PadData = b'\xff' * GetPadSize(ParTree.Data.Size, FFS_COMMON_ALIGNMENT)
                ParTree.Data.ModCheckSum()
                NextTree = ParTree.NextRel
                while NextTree:
                    if NextTree.Data.PeCoffSecIndex:
                        self.RebaseFfs(ParTree, Needed_Space)
                        break
                    else:
                        NextTree = NextTree.NextRel
            # If current node is a Section node
            elif ParTree.type == SECTION_TREE:
                OriData = ParTree.Data.Data
                OriHeaderLen = ParTree.Data.HeaderLength
                ParTree.Data.Data = b''
                # Update its data as adding all the header and data of its child node.
                for item in ParTree.Child:
                    if item.type == SECTION_TREE and item.Data.ExtHeader and item.Data.Type != 0x02:
                        ParTree.Data.Data += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.Data + item.Data.PadData
                    elif item.type == SECTION_TREE and item.Data.ExtHeader and item.Data.Type == 0x02:
                        ParTree.Data.Data += struct2stream(item.Data.Header) + struct2stream(item.Data.ExtHeader) + item.Data.OriData + item.Data.PadData
                    else:
                        ParTree.Data.Data += struct2stream(item.Data.Header) + item.Data.Data + item.Data.PadData
                # If the current section is guided section
                if ParTree.Data.Type == 0x02:
                    guidtool = GUIDTools().__getitem__(struct2stream(ParTree.Data.ExtHeader.SectionDefinitionGuid))
                    if not guidtool.ifexist:
                        logger.error("GuidTool {} is not found when decompressing {} file.\n".format(guidtool.command, ParTree.Parent.Data.Name))
                        raise Exception("Process Failed: GuidTool not found!")
                    # Recompress current data, and recalculate the needed space
                    CompressedData = guidtool.pack(ParTree.Data.Data)
                    Needed_Space = len(CompressedData) - len(ParTree.Data.OriData)
                    ParTree.Data.OriData = CompressedData
                    New_Size = ParTree.Data.HeaderLength + len(CompressedData)
                    ParTree.Data.Header.Size[0] = New_Size % (16**2)
                    ParTree.Data.Header.Size[1] = New_Size % (16**4) //(16**2)
                    ParTree.Data.Header.Size[2] = New_Size // (16**4)
                    ParTree.Data.Size = ParTree.Data.Header.SECTION_SIZE
                    ModifySectionType(ParTree)
                    Needed_Space += ParTree.Data.HeaderLength - OriHeaderLen
                    # Update needed space with Delta_Pad_Size
                    if ParTree.NextRel:
                        New_Pad_Size = GetPadSize(ParTree.Data.Size, SECTION_COMMON_ALIGNMENT)
                        Delta_Pad_Size = New_Pad_Size - len(ParTree.Data.PadData)
                        ParTree.Data.PadData = b'\x00' * New_Pad_Size
                        Needed_Space += Delta_Pad_Size
                    else:
                        ParTree.Data.PadData = b''
                    if Needed_Space < 0:
                        self.Remain_New_Free_Space = len(ParTree.Data.OriData) - len(CompressedData)
                # If current section is not guided section
                elif Needed_Space:
                    ChangeSize(ParTree, -Needed_Space)
                    ModifySectionType(ParTree)
                    # Update needed space with Delta_Pad_Size
                    Needed_Space += ParTree.Data.HeaderLength - OriHeaderLen
                    New_Pad_Size = GetPadSize(ParTree.Data.Size, SECTION_COMMON_ALIGNMENT)
                    Delta_Pad_Size = New_Pad_Size - len(ParTree.Data.PadData)
                    Needed_Space += Delta_Pad_Size
                    ParTree.Data.PadData = b'\x00' * New_Pad_Size
            NewParTree = ParTree.Parent
            ROOT_TYPE = [ROOT_FV_TREE, ROOT_FFS_TREE, ROOT_SECTION_TREE, ROOT_TREE]
            if NewParTree and NewParTree.type not in ROOT_TYPE:
                self.ModifyTest(NewParTree, Needed_Space)
        # If current node have enough space, will recompress all the related node data, return true.
        else:
            self.CompressData(ParTree)
            self.Status = True

    def ReplaceFfs(self, FromAdd) -> bool:
        try:
            logger.debug('Start Replacing Process......')
            TargetFv = self.TargetFfs.Parent
            # If the Fv Header Attributes is EFI_FVB2_ERASE_POLARITY, Child Ffs Header State need be reversed.
            if not FromAdd:
                if TargetFv.Data.Header.Attributes & EFI_FVB2_ERASE_POLARITY:
                        self.NewFfs.Data.Header.State = c_uint8(
                            ~self.NewFfs.Data.Header.State)
                # NewFfs parsing will not calculate the PadSize, thus recalculate.
                self.NewFfs.Data.PadData = b'\xff' * GetPadSize(self.NewFfs.Data.Size, FFS_COMMON_ALIGNMENT)
            if self.NewFfs.Data.Size >= self.TargetFfs.Data.Size:
                Needed_Space = self.NewFfs.Data.Size + len(self.NewFfs.Data.PadData) - self.TargetFfs.Data.Size - len(self.TargetFfs.Data.PadData)
                # If TargetFv have enough free space, just move part of the free space to NewFfs.
                if Needed_Space == 0:
                    Target_index = TargetFv.Child.index(self.TargetFfs)
                    TargetFv.Child.remove(self.TargetFfs)
                    TargetFv.insertChild(self.NewFfs, Target_index)
                    RebaseSize = self.GetRebaseSize(self.NewFfs)
                    CalcuFlag = 1
                    self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                    # Modify TargetFv Header and ExtHeader info.
                    TargetFv.Data.ModFvExt()
                    TargetFv.Data.ModFvSize()
                    TargetFv.Data.ModExtHeaderData()
                    ModifyFvExtData(TargetFv)
                    TargetFv.Data.ModCheckSum()
                    # Recompress from the Fv node to update all the related node data.
                    self.CompressData(TargetFv)
                    # return the Status
                    self.Status = True
                elif TargetFv.Data.Free_Space >= Needed_Space:
                    # Modify TargetFv Child info and BiosTree.
                    TargetFv.Child[-1].Data.Data = b'\xff' * (TargetFv.Data.Free_Space - Needed_Space)
                    TargetFv.Data.Free_Space -= Needed_Space
                    Target_index = TargetFv.Child.index(self.TargetFfs)
                    TargetFv.Child.remove(self.TargetFfs)
                    TargetFv.insertChild(self.NewFfs, Target_index)
                    RebaseSize = self.GetRebaseSize(self.NewFfs)
                    CalcuFlag = 1
                    self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                    # Modify TargetFv Header and ExtHeader info.
                    TargetFv.Data.ModFvExt()
                    TargetFv.Data.ModFvSize()
                    TargetFv.Data.ModExtHeaderData()
                    ModifyFvExtData(TargetFv)
                    TargetFv.Data.ModCheckSum()
                    # Recompress from the Fv node to update all the related node data.
                    self.CompressData(TargetFv)
                    # return the Status
                    self.Status = True
                # If TargetFv do not have enough free space, need move part of the free space of TargetFv's parent Fv to TargetFv/NewFfs.
                else:
                    if TargetFv.type == FV_TREE:
                        self.Status = False
                    else:
                        # Recalculate TargetFv needed space to keep it match the BlockSize setting.
                        Needed_Space -= TargetFv.Data.Free_Space
                        BlockSize = TargetFv.Data.Header.BlockMap[0].Length
                        New_Add_Len = BlockSize - Needed_Space%BlockSize
                        Target_index = TargetFv.Child.index(self.TargetFfs)
                        if New_Add_Len % BlockSize:
                            TargetFv.Child[-1].Data.Data = b'\xff' * New_Add_Len
                            TargetFv.Data.Free_Space = New_Add_Len
                            Needed_Space += New_Add_Len
                            TargetFv.insertChild(self.NewFfs, Target_index)
                            TargetFv.Child.remove(self.TargetFfs)
                        else:
                            TargetFv.Child.remove(self.TargetFfs)
                            TargetFv.Data.Free_Space = 0
                            TargetFv.insertChild(self.NewFfs)
                        RebaseSize = self.GetRebaseSize(self.NewFfs)
                        CalcuFlag = 1
                        self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                        # Encapsulate the Fv Data for update.
                        TargetFv.Data.Data = b''
                        for item in TargetFv.Child:
                            if item.type == FFS_FREE_SPACE:
                                TargetFv.Data.Data += item.Data.Data + item.Data.PadData
                            else:
                                TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                        TargetFv.Data.Size += Needed_Space
                        # Modify TargetFv Data Header and ExtHeader info.
                        TargetFv.Data.Header.FvLength = TargetFv.Data.Size
                        TargetFv.Data.ModFvExt()
                        TargetFv.Data.ModFvSize()
                        TargetFv.Data.ModExtHeaderData()
                        ModifyFvExtData(TargetFv)
                        TargetFv.Data.ModCheckSum()
                        # Start free space calculating and moving process.
                        self.ModifyTest(TargetFv.Parent, Needed_Space)
            else:
                New_Free_Space = self.TargetFfs.Data.Size + len(self.TargetFfs.Data.PadData) - self.NewFfs.Data.Size - len(self.NewFfs.Data.PadData)
                # If TargetFv already have free space, move the new free space into it.
                if TargetFv.Data.Free_Space:
                    TargetFv.Child[-1].Data.Data += b'\xff' * New_Free_Space
                    TargetFv.Data.Free_Space += New_Free_Space
                    Target_index = TargetFv.Child.index(self.TargetFfs)
                    TargetFv.Child.remove(self.TargetFfs)
                    TargetFv.insertChild(self.NewFfs, Target_index)
                # If TargetFv do not have free space, create free space for Fv.
                else:
                    if FromAdd:
                        New_Pad_Tree = BIOSTREE(FFS_PAD)
                        New_Pad_Tree.type = FFS_PAD
                        New_Pad_Tree.Data = FfsNode(b'\xff' * New_Free_Space)
                        New_Pad_Tree.Data.Data = b'\xff' * (New_Free_Space - 24)
                        New_Pad_Tree.Data.Header.Size[0] = New_Free_Space % (16**2)
                        New_Pad_Tree.Data.Header.Size[1] = New_Free_Space % (16**4) //(16**2)
                        New_Pad_Tree.Data.Header.Size[2] = New_Free_Space // (16**4)
                        New_Pad_Tree.Data.Size = New_Pad_Tree.Data.Header.FFS_FILE_SIZE
                        Target_index = TargetFv.Child.index(self.TargetFfs)
                        TargetFv.Child.remove(self.TargetFfs)
                        TargetFv.insertChild(self.NewFfs, Target_index)
                        TargetFv.insertChild(New_Pad_Tree, Target_index+1)
                    else:
                        New_Free_Space_Tree = BIOSTREE('FREE_SPACE')
                        New_Free_Space_Tree.type = FFS_FREE_SPACE
                        New_Free_Space_Tree.Data = FfsNode(b'\xff' * New_Free_Space)
                        TargetFv.Data.Free_Space = New_Free_Space
                        TargetFv.insertChild(New_Free_Space)
                        Target_index = TargetFv.Child.index(self.TargetFfs)
                        TargetFv.Child.remove(self.TargetFfs)
                        TargetFv.insertChild(self.NewFfs, Target_index)
                RebaseSize = self.GetRebaseSize(self.NewFfs)
                CalcuFlag = 1
                self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                TargetFv.Data.Data = b''
                for item in TargetFv.Child:
                    if item.type == FFS_FREE_SPACE:
                        TargetFv.Data.Data += item.Data.Data + item.Data.PadData
                    else:
                        TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                # Modify TargetFv Header and ExtHeader info.
                TargetFv.Data.ModFvExt()
                TargetFv.Data.ModFvSize()
                TargetFv.Data.ModExtHeaderData()
                ModifyFvExtData(TargetFv)
                TargetFv.Data.ModCheckSum()
                # Recompress from the Fv node to update all the related node data.
                self.CompressData(TargetFv)
                self.Status = True
            logger.debug('Done!')
        except Exception as e:
            logger.error(
                "FvHandler ReplaceFfs error!")
            raise(e)
        return self.Status

    def AddFfs(self, TargetOrder=None) -> bool:
        try:
            logger.debug('Start Adding Process......')
            self.TargetOrder = TargetOrder
            # NewFfs parsing will not calculate the PadSize, thus recalculate.
            self.NewFfs.Data.PadData = b'\xff' * GetPadSize(self.NewFfs.Data.Size, FFS_COMMON_ALIGNMENT)
            if self.TargetFfs.type == FFS_FREE_SPACE:
                TargetLen = self.NewFfs.Data.Size + len(self.NewFfs.Data.PadData) - self.TargetFfs.Data.Size - len(self.TargetFfs.Data.PadData)
                TargetFv = self.TargetFfs.Parent
                # If the Fv Header Attributes is EFI_FVB2_ERASE_POLARITY, Child Ffs Header State need be reversed.
                if TargetFv.Data.Header.Attributes & EFI_FVB2_ERASE_POLARITY:
                    self.NewFfs.Data.Header.State = c_uint8(
                        ~self.NewFfs.Data.Header.State)
                # If TargetFv have enough free space, just move part of the free space to NewFfs, split free space to NewFfs and new free space.
                if TargetLen < 0:
                    self.TargetFfs.Data.Data = b'\xff' * (-TargetLen)
                    TargetFv.Data.Free_Space = (-TargetLen)
                    TargetFv.Data.ModFvExt()
                    TargetFv.Data.ModExtHeaderData()
                    ModifyFvExtData(TargetFv)
                    TargetFv.Data.ModCheckSum()
                    if self.TargetOrder != None:
                        TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                    else:
                        TargetFv.insertChild(self.NewFfs, -1)
                    ModifyFfsType(self.NewFfs)
                    RebaseSize = self.GetRebaseSize(self.NewFfs)
                    CalcuFlag = 1
                    self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                    # Recompress from the Fv node to update all the related node data.
                    self.CompressData(TargetFv)
                    self.Status = True
                elif TargetLen == 0:
                    TargetFv.Child.remove(self.TargetFfs)
                    TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                    ModifyFfsType(self.NewFfs)
                    RebaseSize = self.GetRebaseSize(self.NewFfs)
                    CalcuFlag = 1
                    self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                    # Recompress from the Fv node to update all the related node data.
                    self.CompressData(TargetFv)
                    self.Status = True
                # If TargetFv do not have enough free space, need move part of the free space of TargetFv's parent Fv to TargetFv/NewFfs.
                else:
                    if TargetFv.type == FV_TREE:
                        self.Status = False
                    elif TargetFv.type == SEC_FV_TREE:
                        # Recalculate TargetFv needed space to keep it match the BlockSize setting.
                        BlockSize = TargetFv.Data.Header.BlockMap[0].Length
                        New_Add_Len = BlockSize - TargetLen%BlockSize
                        if New_Add_Len % BlockSize:
                            self.TargetFfs.Data.Data = b'\xff' * New_Add_Len
                            self.TargetFfs.Data.Size = New_Add_Len
                            TargetLen += New_Add_Len
                            if self.TargetOrder != None:
                                TargetFv.insertChild(self.NewFfs, -1)
                            else:
                                TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                            TargetFv.Data.Free_Space = New_Add_Len
                        else:
                            TargetFv.Child.remove(self.TargetFfs)
                            TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                            TargetFv.Data.Free_Space = 0
                        ModifyFfsType(self.NewFfs)
                        RebaseSize = self.GetRebaseSize(self.NewFfs)
                        CalcuFlag = 1
                        self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                        ModifyFvSystemGuid(TargetFv)
                        TargetFv.Data.Data = b''
                        for item in TargetFv.Child:
                            if item.type == FFS_FREE_SPACE:
                                TargetFv.Data.Data += item.Data.Data + item.Data.PadData
                            else:
                                TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                        # Encapsulate the Fv Data for update.
                        TargetFv.Data.Size += TargetLen
                        TargetFv.Data.Header.FvLength = TargetFv.Data.Size
                        TargetFv.Data.ModFvExt()
                        TargetFv.Data.ModFvSize()
                        TargetFv.Data.ModExtHeaderData()
                        ModifyFvExtData(TargetFv)
                        TargetFv.Data.ModCheckSum()
                        # Start free space calculating and moving process.
                        self.ModifyTest(TargetFv.Parent, TargetLen)
            else:
                # If TargetFv do not have free space, need directly move part of the free space of TargetFv's parent Fv to TargetFv/NewFfs.
                TargetLen = self.NewFfs.Data.Size + len(self.NewFfs.Data.PadData)
                TargetFv = self.TargetFfs.Parent
                if TargetFv.Data.Header.Attributes & EFI_FVB2_ERASE_POLARITY:
                    self.NewFfs.Data.Header.State = c_uint8(
                        ~self.NewFfs.Data.Header.State)
                if TargetFv.type == FV_TREE:
                    PadSpaceEnough = False
                    for CurFfs in TargetFv.Child:
                        if CurFfs.type == FFS_PAD:
                            if CurFfs.Data.Size + len(CurFfs.Data.PadData) >= self.NewFfs.Data.Size:
                                self.TargetFfs = CurFfs
                                PadSpaceEnough = True
                                break
                    if PadSpaceEnough:
                        self.ReplaceFfs(PadSpaceEnough)
                    else:
                        self.Status = False
                elif TargetFv.type == SEC_FV_TREE:
                    BlockSize = TargetFv.Data.Header.BlockMap[0].Length
                    New_Add_Len = BlockSize - TargetLen%BlockSize
                    if New_Add_Len % BlockSize:
                        New_Free_Space = BIOSTREE('FREE_SPACE')
                        New_Free_Space.type = FFS_FREE_SPACE
                        New_Free_Space.Data = FreeSpaceNode(b'\xff' * New_Add_Len)
                        TargetLen += New_Add_Len
                        TargetFv.Data.Free_Space = New_Add_Len
                        TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                        TargetFv.insertChild(New_Free_Space)
                    else:
                        TargetFv.insertChild(self.NewFfs, self.TargetOrder)
                    ModifyFfsType(self.NewFfs)
                    RebaseSize = self.GetRebaseSize(self.NewFfs)
                    CalcuFlag = 1
                    self.RebaseFfs(self.NewFfs, RebaseSize, CalcuFlag)
                    ModifyFvSystemGuid(TargetFv)
                    TargetFv.Data.Data = b''
                    for item in TargetFv.Child:
                        if item.type == FFS_FREE_SPACE:
                            TargetFv.Data.Data += item.Data.Data + item.Data.PadData
                        else:
                            TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                    TargetFv.Data.Size += TargetLen
                    TargetFv.Data.Header.FvLength = TargetFv.Data.Size
                    TargetFv.Data.ModFvExt()
                    TargetFv.Data.ModFvSize()
                    TargetFv.Data.ModExtHeaderData()
                    ModifyFvExtData(TargetFv)
                    TargetFv.Data.ModCheckSum()
                    self.ModifyTest(TargetFv.Parent, TargetLen)
            logger.debug('Done!')
        except Exception as e:
            logger.error(
                "FvHandler AddFfs error!")
            raise(e)
        return self.Status

    def DeleteFfs(self) -> bool:
        try:
            logger.debug('Start Deleting Process......')
            Delete_Ffs = self.TargetFfs
            Delete_Fv = Delete_Ffs.Parent
            # Calculate free space
            Add_Free_Space = Delete_Ffs.Data.Size + len(Delete_Ffs.Data.PadData)
            # If Ffs parent Fv have free space, follow the rules to merge the new free space.
            if Delete_Fv.Data.Free_Space:
                # If Fv is a Section fv, free space need to be recalculated to keep align with BlockSize.
                # Other free space saved in self.Remain_New_Free_Space, will be moved to the 1st level Fv.
                if Delete_Fv.type == SEC_FV_TREE:
                    Used_Size = Delete_Fv.Data.Size - Delete_Fv.Data.Free_Space - Add_Free_Space
                    BlockSize = Delete_Fv.Data.Header.BlockMap[0].Length
                    New_Free_Space = BlockSize - Used_Size % BlockSize
                    self.Remain_New_Free_Space += Delete_Fv.Data.Free_Space + Add_Free_Space - New_Free_Space
                    Delete_Fv.Child[-1].Data.Data = New_Free_Space * b'\xff'
                    Delete_Fv.Data.Free_Space = New_Free_Space
                # If Fv is lst level Fv, new free space will be merged with origin free space.
                else:
                    Used_Size = Delete_Fv.Data.Size - Delete_Fv.Data.Free_Space - Add_Free_Space
                    Delete_Fv.Child[-1].Data.Data += Add_Free_Space * b'\xff'
                    Delete_Fv.Data.Free_Space += Add_Free_Space
                    New_Free_Space = Delete_Fv.Data.Free_Space
            # If Ffs parent Fv not have free space, will create new free space node to save the free space.
            else:
                # If Fv is a Section fv, new free space need to be recalculated to keep align with BlockSize.
                # Then create a Free spcae node to save the 0xff data, and insert into the Fv.
                # If have more space left, move to 1st level fv.
                if Delete_Fv.type == SEC_FV_TREE:
                    Used_Size = Delete_Fv.Data.Size - Add_Free_Space
                    BlockSize = Delete_Fv.Data.Header.BlockMap[0].Length
                    New_Free_Space = BlockSize - Used_Size % BlockSize
                    self.Remain_New_Free_Space += Add_Free_Space - New_Free_Space
                    Add_Free_Space = New_Free_Space
                # If Fv is lst level Fv, new free space node will be created to save the free space.
                else:
                    Used_Size = Delete_Fv.Data.Size - Add_Free_Space
                    New_Free_Space = Add_Free_Space
                New_Free_Space_Info = FfsNode(Add_Free_Space * b'\xff')
                New_Free_Space_Info.Data = Add_Free_Space * b'\xff'
                New_Ffs_Tree = BIOSTREE(New_Free_Space_Info.Name)
                New_Ffs_Tree.type = FFS_FREE_SPACE
                New_Ffs_Tree.Data = New_Free_Space_Info
                Delete_Fv.insertChild(New_Ffs_Tree)
                Delete_Fv.Data.Free_Space = Add_Free_Space
            IfRebase = False
            while Delete_Ffs.NextRel:
                CurFfs = Delete_Ffs.NextRel
                if CurFfs.Data.PeCoffSecIndex != None:
                    IfRebase = True
                    break
            Delete_Fv.Child.remove(Delete_Ffs)
            if IfRebase:
                RebaseSize = self.GetRebaseSize(CurFfs)
                CalcuFlag = 1
                self.RebaseFfs(CurFfs, RebaseSize, CalcuFlag)
            Delete_Fv.Data.Header.FvLength = Used_Size + New_Free_Space
            Delete_Fv.Data.ModFvExt()
            Delete_Fv.Data.ModFvSize()
            Delete_Fv.Data.ModExtHeaderData()
            ModifyFvExtData(Delete_Fv)
            Delete_Fv.Data.ModCheckSum()
            # Recompress from the Fv node to update all the related node data.
            self.CompressData(Delete_Fv)
            self.Status = True
            logger.debug('Done!')
        except Exception as e:
            logger.error(
                "FvHandler DeleteFfs error!")
            raise(e)
        return self.Status

    def ShrinkFv(self) -> bool:
        try:
            TargetFv = self.NewFfs
            TargetFv.Data.Data = b''
            if not TargetFv.Data.Free_Space:
                self.Status = True
            else:
                BlockSize = TargetFv.Data.Header.BlockMap[0].Length
                New_Free_Space = TargetFv.Data.Free_Space%BlockSize
                Removed_Space = TargetFv.Data.Free_Space - New_Free_Space
                TargetFv.Child[-1].Data.Data = b'\xff' * New_Free_Space
                TargetFv.Data.Size -= Removed_Space
                TargetFv.Data.Header.Fvlength = TargetFv.Data.Size
                ModifyFvSystemGuid(TargetFv)
                for item in TargetFv.Child:
                    if item.type == FFS_FREE_SPACE:
                        TargetFv.Data.Data += item.Data.Data + item.Data.PadData
                    else:
                        TargetFv.Data.Data += struct2stream(item.Data.Header)+ item.Data.Data + item.Data.PadData
                TargetFv.Data.ModFvExt()
                TargetFv.Data.ModFvSize()
                TargetFv.Data.ModExtHeaderData()
                ModifyFvExtData(TargetFv)
                TargetFv.Data.ModCheckSum()
                self.Status = True
        except Exception as e:
            logger.error(
                "FvHandler ShrinkFv error!")
            raise(e)
        return self.Status

    def GetRebaseSize(self, TargetFfs)->int:
        RebaseSize = 0
        FfsDataOffset = 0
        SecOffset = 0
        if TargetFfs.Parent.type == FV_TREE or TargetFfs.Parent.type == ROOT_FV_TREE:
            if TargetFfs.Data.PeCoffSecIndex != None:
                TargetFv = TargetFfs.Parent
                TargetFfsIndex = TargetFv.Child.index(TargetFfs)
                BaseAddress = TargetFv.Data.BaseAddress
                TarSecNode = TargetFfs.Child[TargetFfs.Data.PeCoffSecIndex]
                TarPeCoffNode = TarSecNode.Child[0]
                for CalIndex in range(TargetFfsIndex):
                    FfsDataOffset += TargetFv.Child[CalIndex].Data.Size + len(TargetFv.Child[CalIndex].Data.PadData)
                for CalIndex in range(TargetFfs.Data.PeCoffSecIndex):
                    SecOffset += TargetFfs.Child[CalIndex].Data.Size + len(TargetFfs.Child[CalIndex].Data.PadData)
                if TarPeCoffNode.Data.TeHeader:
                    RebaseSize = BaseAddress + TargetFv.Data.HeaderLength + FfsDataOffset + TargetFfs.Data.HeaderLength + SecOffset + \
                                TarSecNode.Data.HeaderLength + EFI_TE_IMAGE_HEADER_SIZE - TarPeCoffNode.Data.TeHeader.StrippedSize
                elif TarPeCoffNode.Data.PeHeader:
                    RebaseSize = BaseAddress + TargetFv.Data.HeaderLength + FfsDataOffset + TargetFfs.Data.HeaderLength + SecOffset + \
                                TarSecNode.Data.HeaderLength
        return RebaseSize

    def RebaseFfs(self, TargetFfs, RebaseSize, CalcuFlag=0) -> None:
        TargetFv = TargetFfs.Parent
        if TargetFv.type == FV_TREE or TargetFv.type == ROOT_FV_TREE:
            Target_Index = TargetFv.Child.index(TargetFfs)
            ChildFfsNum = len(TargetFv.Child)
            NewAddedOffset = TargetFfs.Data.Size + len(TargetFfs.Data.PadData)
            for RebaseFfsIndex in range(Target_Index, ChildFfsNum, 1):
                CurTargetFfs = TargetFv.Child[RebaseFfsIndex]
                if CurTargetFfs.type == FFS_FREE_SPACE or CurTargetFfs.type == FFS_PAD:
                    break
                CurTargetFfs.Data.Data = b''
                for EachSection in CurTargetFfs.Child:
                    if EachSection.Data.Type == EFI_SECTION_PE32 or EachSection.Data.Type == EFI_SECTION_TE:
                        if EachSection.Child and EachSection.Child[0].type==PECOFF_TREE:
                            PeCoffTree = EachSection.Child[0]
                            PeCoffTree.Data.PeCoffRebase(RebaseSize, CalcuFlag)
                            EachSection.Data.Data = PeCoffTree.Data.Data
                            CurTargetFfs.Data.Data += struct2stream(EachSection.Data.Header) + PeCoffTree.Data.Data
                    elif EachSection.type == SECTION_TREE and not EachSection.Data.OriData and EachSection.Data.ExtHeader:
                        CurTargetFfs.Data.Data += struct2stream(EachSection.Data.Header) + struct2stream(EachSection.Data.ExtHeader) + EachSection.Data.Data + EachSection.Data.PadData
                    elif EachSection.type == SECTION_TREE and EachSection.Data.OriData and not EachSection.Data.ExtHeader:
                        CurTargetFfs.Data.Data += struct2stream(EachSection.Data.Header) + EachSection.Data.OriData + EachSection.Data.PadData
                    elif EachSection.type == SECTION_TREE and EachSection.Data.OriData and EachSection.Data.ExtHeader:
                        CurTargetFfs.Data.Data += struct2stream(EachSection.Data.Header) + struct2stream(EachSection.Data.ExtHeader) + EachSection.Data.OriData + EachSection.Data.PadData
                    elif EachSection.type == SECTION_TREE:
                        CurTargetFfs.Data.Data += struct2stream(EachSection.Data.Header) + EachSection.Data.Data + EachSection.Data.PadData
                if CurTargetFfs.NextRel:
                    CalcuFlag = 0
                    RebaseSize = NewAddedOffset
