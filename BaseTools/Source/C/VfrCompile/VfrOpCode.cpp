/** @file

  The definition of CFormPkg's member function

Copyright (c) 2004 - 2019, Intel Corporation. All rights reserved.<BR>
SPDX-License-Identifier: BSD-2-Clause-Patent

**/

#include "stdio.h"
#include "assert.h"
#include "VfrOpCode.h"

COpCodeDB::COpCodeDB ()
{
  mOpCodeList = new SOpNode;
  mOpCodeOneofNodeList = new SOpInfoOneofNode;
  mOpCodeList->mNext = NULL;
  mOpCodeOneofNodeList->mNext = NULL;

  mCurOpCode = mOpCodeList;
  mCurOpCodeOneofNode = mOpCodeOneofNodeList;

  mOneOfNum = 0;
}

VOID
COpCodeDB::AddNewOpNode(
  IN SOpNode *New
  )
{
  mCurOpCode->mNext       = New;
  mCurOpCode              = New;
}

VOID
COpCodeDB::AddNewOpOneOfNode (
  IN SOpNode *New
  )
{

  SOpInfoOneofNode  *NewOneOfNode = new SOpInfoOneofNode;
  NewOneOfNode->mNext = NULL;
  NewOneOfNode->AddOneOfInfo = FALSE;
  if (mCurOpCodeOneofNode->AddOneOfInfo){
    if (New->Header.OpCode == EFI_IFR_ONE_OF_OP | New->Header.OpCode == EFI_IFR_ORDERED_LIST_OP){
      mCurOpCodeOneofNode->mNext = NewOneOfNode;
      mCurOpCodeOneofNode = NewOneOfNode;
      printf("Have moved to next OneOf!\n");
    }
  }
  if (New->Header.OpCode == EFI_IFR_ONE_OF_OP | New->Header.OpCode == EFI_IFR_ORDERED_LIST_OP){
    mCurOpCodeOneofNode->OpOneOfNode = New;
    mOneOfNum += 1;
    printf("mCurOpCodeOneofNode has %d item now.\n", mOneOfNum);
  }
  if (New->Header.OpCode == EFI_IFR_ONE_OF_OPTION_OP){
    mCurOpCodeOneofNode->AddOneOfInfo = TRUE;
  }
}
