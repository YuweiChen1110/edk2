/** @file

  The definition of CFormPkg's member function

Copyright (c) 2004 - 2019, Intel Corporation. All rights reserved.<BR>
SPDX-License-Identifier: BSD-2-Clause-Patent

**/

#ifndef _VFROPCODE_H_
#define _VFROPCODE_H_

#include "VfrUtilityLib.h"
#include "Common/UefiInternalFormRepresentation.h"

struct SOpNode{
  EFI_IFR_OP_HEADER        Header;
  EFI_IFR_QUESTION_HEADER  QuestionHeader;         // EFI_IFR_CHECKBOX | EFI_IFR_REF | EFI_IFR_REF2
  EFI_IFR_STATEMENT_HEADER StatementHeader;        // EFI_IFR_SUBTITLE | EFI_IFR_TEXT
  EFI_STRING_ID            DefaultName;            // EFI_IFR_DEFAULTSTORE
  EFI_GUID                 Guid;                   // EFI_IFR_VARSTORE | EFI_IFR_VARSTORE_EFI | EFI_IFR_VARSTORE_NAME_VALUE | EFI_IFR_FORM_SET
  EFI_VARSTORE_ID          VarStoreId;             // EFI_IFR_VARSTORE | EFI_IFR_VARSTORE_EFI | EFI_IFR_VARSTORE_NAME_VALUE
  UINT16                   Size;                   // EFI_IFR_VARSTORE
  UINT8                    Name[1];                // EFI_IFR_VARSTORE
  UINT32                   Attributes;             // EFI_IFR_VARSTORE_EFI
  EFI_STRING_ID            FormSetTitle;           // EFI_IFR_FORM_SET
  EFI_STRING_ID            Help;                   // EFI_IFR_FORM_SET
  UINT8                    Flags;                  // EFI_IFR_FORM_SET | EFI_IFR_SUBTITLE | EFI_IFR_CHECKBOX | EFI_IFR_ONE_OF_OPTION
  UINT16                   FormId;                 // EFI_IFR_FORM
  EFI_STRING_ID            FormTitle;              // EFI_IFR_FORM
  EFI_IMAGE_ID             Id;                     // EFI_IFR_IMAGE
  UINT8                    RuleId;                 // EFI_IFR_RULE
  UINT16                   DefaultId;              // EFI_IFR_DEFAULTSTORE | EFI_IFR_DEFAULT | EFI_IFR_DEFAULT_2
  UINT8                    Type;                   // EFI_IFR_DEFAULT | EFI_IFR_DEFAULT_2 | EFI_IFR_ONE_OF_OPTION
  EFI_IFR_TYPE_VALUE       Value;                  // EFI_IFR_DEFAULT | EFI_IFR_ONE_OF_OPTION
  EFI_STRING_ID            TextTwo;                // EFI_IFR_TEXT
  EFI_FORM_ID              FormId_Ref;             // EFI_IFR_REF | EFI_IFR_REF2 | EFI_IFR_REF3 | EFI_IFR_REF4
  EFI_QUESTION_ID          QuestionId;             // EFI_IFR_REF2 | EFI_IFR_REF3 | EFI_IFR_REF4
  EFI_GUID                 FormSetId;              // EFI_IFR_REF3 | EFI_IFR_REF4
  EFI_STRING_ID            DevicePath;             // EFI_IFR_REF4
  MINMAXSTEP_DATA          data;
  EFI_STRING_ID            Option;                 // EFI_IFR_ONE_OF_OPTION
  UINT8                    ExtendOpCode;           // EFI_IFR_GUID_CLASS | EFI_IFR_GUID_SUBCLASS
  UINT16                   Class;                  // EFI_IFR_GUID_CLASS
  UINT16                   SubClass;               // EFI_IFR_GUID_SUBCLASS
  EFI_GUID                 *ClassGuid;             // Formset ClassGuid
  UINT8                    ClassGuidNum;           // Formset ClassGuidNum
  union {
    EFI_STRING_ID          VarName;
    UINT16                 VarOffset;
  }                        VarStoreInfo;           // EFI_IFR_GET | EFI_IFR_SET
  EFI_STRING_ID            QuestionConfig;         // EFI_IFR_ACTION
  UINT8                    StringMinSize;          // EFI_IFR_STRING
  UINT8                    StringMaxSize;          // EFI_IFR_STRING
  UINT16                   PasswordMinSize;        // EFI_IFR_PASSWORD
  UINT16                   PasswordMaxSize;        // EFI_IFR_PASSWORD
  UINT8                    MaxContainers;          // EFI_IFR_ORDERED_LIST
  EFI_STRING_ID            Error;
  EFI_STRING_ID            Warning;
  UINT8                    TimeOut;
  UINT8                    RefreshInterval;        // EFI_IFR_REFRESH
  EFI_GUID                 RefreshEventGroupId;    // EFI_IFR_REFRESH_ID
  EFI_STRING_ID            Title;                  // EFI_IFR_GUID_BANNER
  UINT16                   LineNumber;             // EFI_IFR_GUID_BANNER
  UINT8                    Alignment;              // EFI_IFR_GUID_BANNER
  EFI_IFR_TYPE_VALUE       OptionValue;            // EFI_IFR_GUID_OPTIONKEY
  UINT16                   KeyValue;               // EFI_IFR_GUID_OPTIONKEY
  UINT16                   NameId;                 // EFI_IFR_GUID_VAREQNAME
  EFI_QUESTION_ID          QuestionId1;            // EFI_IFR_EQ_ID_ID
  EFI_QUESTION_ID          QuestionId2;            // EFI_IFR_EQ_ID_ID
  UINT16                   mEqIdVal_Value;         // EFI_IFR_EQ_ID_VAL
  UINT16                   ListLength;             // EFI_IFR_EQ_ID_VAL_LIST
  UINT16                   ValueList[1];           // EFI_IFR_EQ_ID_VAL_LIST
  EFI_STRING_ID            StringId;               // EFI_IFR_STRING_REF1
  EFI_GUID                 Permissions;            // EFI_IFR_SECURITY
  UINT8                    Format;                 // EFI_IFR_TO_STRING
  UINT8                    Condition[1];           // Condition
  UINT16                   LabelNumber;            // EFI_IFR_LABEL_OP
  struct                   SOpNode *mNext;
};

struct SOpInfoOneofNode{
  SOpNode           *OpOneOfNode;
  SOpNode           *OpOptionNode;
  BOOLEAN           AddOneOfInfo;
  struct SOpInfoOneofNode  *mNext;
};

class COpCodeDB{

private:
  SOpNode             *mOpCodeList;
  SOpInfoOneofNode    *mOpCodeOneofNodeList;
  SOpNode             *mCurOpCode;
  SOpInfoOneofNode    *mCurOpCodeOneofNode;
  // SOpInfoOptionNode   *mOpCodeOptionNodeList;
public:
  COpCodeDB (VOID);
  VOID                AddNewOpNode (IN SOpNode *);
  VOID                AddNewOpOneOfNode (IN SOpNode *);
  int                 mOneOfNum;
  inline SOpNode * GetOpCodeList (VOID) {
    return mOpCodeList;
  }
  inline SOpInfoOneofNode * GetOpCodeOneOfNodeList (VOID) {
    return mOpCodeOneofNodeList;
  }
  // inline SOpInfoOptionNode * GetOpCodeOptionNodeList (VOID) {
  //   return mOpCodeOptionNodeList;
  // }
private:
  COpCodeDB (IN CONST COpCodeDB&);             // Prevent copy-construction
  COpCodeDB& operator= (IN CONST COpCodeDB&);  // Prevent assignment
};

extern COpCodeDB       gCOpCodeDB;

#endif