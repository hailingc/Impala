#!/usr/bin/env impala-python
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from string import Template
import os
import shutil
import filecmp
import tempfile
from optparse import OptionParser

parser = OptionParser()
parser.add_option("--noclean", action="store_true", default=False,
                  help="If specified, does not remove existing files and only replaces "
                       "them with freshly generated ones if they have changed.")
options, args = parser.parse_args()

# This script will generate two headers that describe all of the clang cross compiled
# functions.
# The script outputs (run: 'impala/common/function-registry/gen_functions.py')
#   - be/src/generated-sources/impala-ir/impala-ir-functions.h
#     This file contains enums for all of the cross compiled functions
#   - be/src/generated-sources/impala-ir/impala-ir-function-names.h
#     This file contains a mapping of <string, enum>

# Mapping of enum to compiled function name. The compiled function name has to be
# the actual mangled compiler generated name. One can easily obtain that by disassembling
# the bit code module.
# TODO: should we work out the mangling rules?
ir_functions = [
  ["AGG_NODE_PROCESS_ROW_BATCH_WITH_GROUPING",
   "_ZN6impala15AggregationNode27ProcessRowBatchWithGroupingEPNS_8RowBatchE"],
  ["AGG_NODE_PROCESS_ROW_BATCH_NO_GROUPING",
   "_ZN6impala15AggregationNode25ProcessRowBatchNoGroupingEPNS_8RowBatchE"],
  ["AGG_NODE_GET_EXPR_CTX",
   "_ZNK6impala15AggregationNode13GetAggExprCtxEi"],
  ["AGG_NODE_GET_FN_CTX",
   "_ZNK6impala15AggregationNode11GetAggFnCtxEi"],
  ["PART_AGG_NODE_PROCESS_BATCH_UNAGGREGATED",
   "_ZN6impala26PartitionedAggregationNode12ProcessBatchILb0EEENS_6StatusEPNS_8RowBatchENS_13TPrefetchMode4typeEPNS_12HashTableCtxE"],
  ["PART_AGG_NODE_PROCESS_BATCH_AGGREGATED",
   "_ZN6impala26PartitionedAggregationNode12ProcessBatchILb1EEENS_6StatusEPNS_8RowBatchENS_13TPrefetchMode4typeEPNS_12HashTableCtxE"],
  ["PART_AGG_NODE_PROCESS_BATCH_NO_GROUPING",
   "_ZN6impala26PartitionedAggregationNode22ProcessBatchNoGroupingEPNS_8RowBatchE"],
  ["PART_AGG_NODE_PROCESS_BATCH_STREAMING",
   "_ZN6impala26PartitionedAggregationNode21ProcessBatchStreamingEbNS_13TPrefetchMode4typeEPNS_8RowBatchES4_PNS_12HashTableCtxEPi"],
  ["PART_AGG_NODE_GET_EXPR_CTXS",
   "_ZNK6impala26PartitionedAggregationNode18GetAggExprContextsEi"],
  ["AVG_UPDATE_BIGINT",
   "_ZN6impala18AggregateFunctions9AvgUpdateIN10impala_udf9BigIntValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["AVG_UPDATE_DOUBLE",
   "_ZN6impala18AggregateFunctions9AvgUpdateIN10impala_udf9DoubleValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["AVG_UPDATE_TIMESTAMP",
   "_ZN6impala18AggregateFunctions18TimestampAvgUpdateEPN10impala_udf15FunctionContextERKNS1_12TimestampValEPNS1_9StringValE"],
  ["AVG_UPDATE_DECIMAL",
   "_ZN6impala18AggregateFunctions16DecimalAvgUpdateEPN10impala_udf15FunctionContextERKNS1_10DecimalValEPNS1_9StringValE"],
  ["AVG_MERGE",
   "_ZN6impala18AggregateFunctions8AvgMergeEPN10impala_udf15FunctionContextERKNS1_9StringValEPS4_"],
  ["AVG_MERGE_DECIMAL",
   "_ZN6impala18AggregateFunctions15DecimalAvgMergeEPN10impala_udf15FunctionContextERKNS1_9StringValEPS4_"],
  ["CODEGEN_ANYVAL_STRING_VAL_EQ",
   "_Z11StringValEqRKN10impala_udf9StringValES2_"],
  ["CODEGEN_ANYVAL_STRING_VALUE_EQ",
   "_Z13StringValueEqRKN10impala_udf9StringValERKN6impala11StringValueE"],
  ["CODEGEN_ANYVAL_TIMESTAMP_VAL_EQ",
   "_Z14TimestampValEqRKN10impala_udf12TimestampValES2_"],
  ["CODEGEN_ANYVAL_TIMESTAMP_VALUE_EQ",
   "_Z16TimestampValueEqRKN10impala_udf12TimestampValERKN6impala14TimestampValueE"],
  ["EXPR_GET_BOOLEAN_VAL",
   "_ZN6impala4Expr13GetBooleanValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_TINYINT_VAL",
   "_ZN6impala4Expr13GetTinyIntValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_SMALLINT_VAL",
   "_ZN6impala4Expr14GetSmallIntValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_INT_VAL",
   "_ZN6impala4Expr9GetIntValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_BIGINT_VAL",
   "_ZN6impala4Expr12GetBigIntValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_FLOAT_VAL",
   "_ZN6impala4Expr11GetFloatValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_DOUBLE_VAL",
   "_ZN6impala4Expr12GetDoubleValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_STRING_VAL",
   "_ZN6impala4Expr12GetStringValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_TIMESTAMP_VAL",
   "_ZN6impala4Expr15GetTimestampValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["EXPR_GET_DECIMAL_VAL",
   "_ZN6impala4Expr13GetDecimalValEPS0_PNS_11ExprContextEPKNS_8TupleRowE"],
  ["HASH_CRC", "IrCrcHash"],
  ["HASH_FNV", "IrFnvHash"],
  ["HASH_MURMUR", "IrMurmurHash"],
  ["HASH_JOIN_PROCESS_BUILD_BATCH",
   "_ZN6impala12HashJoinNode17ProcessBuildBatchEPNS_8RowBatchE"],
  ["HASH_JOIN_PROCESS_PROBE_BATCH",
   "_ZN6impala12HashJoinNode17ProcessProbeBatchEPNS_8RowBatchES2_i"],
  ["OLD_HASH_TABLE_GET_BUILD_EXPR_CTXS",
   "_ZNK6impala12OldHashTable15build_expr_ctxsEv"],
  ["OLD_HASH_TABLE_GET_PROBE_EXPR_CTXS",
   "_ZNK6impala12OldHashTable15probe_expr_ctxsEv"],
  ["OLD_HASH_TABLE_GET_EXPR_VALUES_BUFFER",
   "_ZNK6impala12OldHashTable18expr_values_bufferEv"],
  ["OLD_HASH_TABLE_GET_EXPR_VALUE_NULL_BITS",
   "_ZNK6impala12OldHashTable20expr_value_null_bitsEv"],
  ["PHJ_PROCESS_BUILD_BATCH",
   "_ZN6impala10PhjBuilder17ProcessBuildBatchEPNS_8RowBatchEPNS_12HashTableCtxEb"],
  ["PHJ_PROCESS_PROBE_BATCH_INNER_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi0EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_LEFT_OUTER_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi1EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_LEFT_SEMI_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi2EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_LEFT_ANTI_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi3EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_NULL_AWARE_LEFT_ANTI_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi4EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_RIGHT_OUTER_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi5EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_RIGHT_SEMI_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi6EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_RIGHT_ANTI_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi7EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_PROCESS_PROBE_BATCH_FULL_OUTER_JOIN",
   "_ZN6impala23PartitionedHashJoinNode17ProcessProbeBatchILi8EEEiNS_13TPrefetchMode4typeEPNS_8RowBatchEPNS_12HashTableCtxEPNS_6StatusE"],
  ["PHJ_INSERT_BATCH",
   "_ZN6impala10PhjBuilder9Partition11InsertBatchENS_13TPrefetchMode4typeEPNS_12HashTableCtxEPNS_8RowBatchERKSt6vectorINS_19BufferedTupleStream6RowIdxESaISA_EE"],
  ["HASH_TABLE_GET_HASH_SEED",
   "_ZNK6impala12HashTableCtx11GetHashSeedEv"],
  ["HASH_TABLE_GET_BUILD_EXPR_CTX",
   "_ZNK6impala12HashTableCtx16GetBuildExprCtxsEv"],
  ["HASH_TABLE_GET_PROBE_EXPR_CTX",
   "_ZNK6impala12HashTableCtx16GetProbeExprCtxsEv"],
  ["HLL_UPDATE_BOOLEAN",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf10BooleanValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_TINYINT",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf10TinyIntValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_SMALLINT",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf11SmallIntValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_INT",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf6IntValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_BIGINT",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf9BigIntValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_FLOAT",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf8FloatValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_DOUBLE",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf9DoubleValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_STRING",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf9StringValEEEvPNS2_15FunctionContextERKT_PS3_"],
  ["HLL_UPDATE_TIMESTAMP",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf12TimestampValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_UPDATE_DECIMAL",
   "_ZN6impala18AggregateFunctions9HllUpdateIN10impala_udf10DecimalValEEEvPNS2_15FunctionContextERKT_PNS2_9StringValE"],
  ["HLL_MERGE",
   "_ZN6impala18AggregateFunctions8HllMergeEPN10impala_udf15FunctionContextERKNS1_9StringValEPS4_"],
  ["DECODE_AVRO_DATA",
   "_ZN6impala15HdfsAvroScanner14DecodeAvroDataEiPNS_7MemPoolEPPhS3_PNS_5TupleEPNS_8TupleRowE"],
  ["READ_UNION_TYPE",
   "_ZN6impala15HdfsAvroScanner13ReadUnionTypeEiPPhS1_Pb"],
  ["READ_AVRO_BOOLEAN",
   "_ZN6impala15HdfsAvroScanner15ReadAvroBooleanENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_INT32",
   "_ZN6impala15HdfsAvroScanner13ReadAvroInt32ENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_INT64",
   "_ZN6impala15HdfsAvroScanner13ReadAvroInt64ENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_FLOAT",
   "_ZN6impala15HdfsAvroScanner13ReadAvroFloatENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_DOUBLE",
   "_ZN6impala15HdfsAvroScanner14ReadAvroDoubleENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_STRING",
   "_ZN6impala15HdfsAvroScanner14ReadAvroStringENS_13PrimitiveTypeEPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_VARCHAR",
   "_ZN6impala15HdfsAvroScanner15ReadAvroVarcharENS_13PrimitiveTypeEiPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_CHAR",
   "_ZN6impala15HdfsAvroScanner12ReadAvroCharENS_13PrimitiveTypeEiPPhS2_bPvPNS_7MemPoolE"],
  ["READ_AVRO_DECIMAL",
   "_ZN6impala15HdfsAvroScanner15ReadAvroDecimalEiPPhS1_bPvPNS_7MemPoolE"],
  ["HDFS_SCANNER_WRITE_ALIGNED_TUPLES",
   "_ZN6impala11HdfsScanner18WriteAlignedTuplesEPNS_7MemPoolEPNS_8TupleRowEiPNS_13FieldLocationEiiii"],
  ["HDFS_SCANNER_GET_CONJUNCT_CTX",
   "_ZNK6impala11HdfsScanner14GetConjunctCtxEi"],
  ["PROCESS_SCRATCH_BATCH",
   "_ZN6impala18HdfsParquetScanner19ProcessScratchBatchEPNS_8RowBatchE"],
  ["PARQUET_SCANNER_EVAL_RUNTIME_FILTER",
   "_ZN6impala18HdfsParquetScanner17EvalRuntimeFilterEiPNS_8TupleRowE"],
  ["STRING_TO_BOOL", "IrStringToBool"],
  ["STRING_TO_INT8", "_Z14IrStringToInt8PKciPN6impala12StringParser11ParseResultE"],
  ["STRING_TO_INT16", "IrStringToInt16"],
  ["STRING_TO_INT32", "IrStringToInt32"],
  ["STRING_TO_INT64", "IrStringToInt64"],
  ["STRING_TO_FLOAT", "IrStringToFloat"],
  ["STRING_TO_DOUBLE", "IrStringToDouble"],
  ["IS_NULL_STRING", "IrIsNullString"],
  ["GENERIC_IS_NULL_STRING", "IrGenericIsNullString"],
  ["RAW_VALUE_COMPARE",
   "_ZN6impala8RawValue7CompareEPKvS2_RKNS_10ColumnTypeE"],
  ["TOPN_NODE_INSERT_BATCH",
   "_ZN6impala8TopNNode11InsertBatchEPNS_8RowBatchE"],
  ["MEMPOOL_ALLOCATE",
   "_ZN6impala7MemPool8AllocateILb0EEEPhli"],
  ["MEMPOOL_CHECKED_ALLOCATE",
   "_ZN6impala7MemPool8AllocateILb1EEEPhli"],
  ["RUNTIME_FILTER_EVAL",
   "_ZNK6impala13RuntimeFilter4EvalEPvRKNS_10ColumnTypeE"]
]

enums_preamble = '\
//\n\
// Licensed under the Apache License, Version 2.0 (the "License");\n\
// you may not use this file except in compliance with the License.\n\
// You may obtain a copy of the License at\n\
//\n\
// http://www.apache.org/licenses/LICENSE-2.0\n\
//\n\
// Unless required by applicable law or agreed to in writing, software\n\
// distributed under the License is distributed on an "AS IS" BASIS,\n\
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n\
// See the License for the specific language governing permissions and\n\
// limitations under the License.\n\
\n\
// This is a generated file, DO NOT EDIT IT.\n\
// To add new functions, see be/src/codegen/gen_ir_descriptions.py.\n\
\n\
#ifndef IMPALA_IR_FUNCTIONS_H\n\
#define IMPALA_IR_FUNCTIONS_H\n\
\n\
namespace impala {\n\
\n\
class IRFunction {\n\
 public:\n\
  enum Type {\n'

enums_epilogue = '\
  };\n\
};\n\
\n\
}\n\
\n\
#endif\n'

names_preamble = '\
//\n\
// Licensed under the Apache License, Version 2.0 (the "License");\n\
// you may not use this file except in compliance with the License.\n\
// You may obtain a copy of the License at\n\
//\n\
// http://www.apache.org/licenses/LICENSE-2.0\n\
//\n\
// Unless required by applicable law or agreed to in writing, software\n\
// distributed under the License is distributed on an "AS IS" BASIS,\n\
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n\
// See the License for the specific language governing permissions and\n\
// limitations under the License.\n\
\n\
// This is a generated file, DO NOT EDIT IT.\n\
// To add new functions, see be/src/codegen/gen_ir_descriptions.py.\n\
\n\
#ifndef IMPALA_IR_FUNCTION_NAMES_H\n\
#define IMPALA_IR_FUNCTION_NAMES_H\n\
\n\
#include "impala-ir/impala-ir-functions.h"\n\
\n\
namespace impala {\n\
\n\
static struct {\n\
  std::string fn_name; \n\
  IRFunction::Type fn; \n\
} FN_MAPPINGS[] = {\n'

names_epilogue = '\
};\n\
\n\
}\n\
\n\
#endif\n'

def move_if_different(src_file, dest_file):
  """Moves src_file to dest_file if dest_file does not exist, or if
  the contents of src_file and dest_file differ. Assumes that src_file exists."""
  if not os.path.isfile(dest_file) or not filecmp.cmp(src_file, dest_file):
    shutil.move(src_file, dest_file)
  else:
    print 'Retaining existing file: %s' % (dest_file)

BE_PATH = os.path.join(os.environ['IMPALA_HOME'], 'be/generated-sources/impala-ir/')
IR_FUNCTIONS_FILE = 'impala-ir-functions.h'
IR_NAMES_FILE = 'impala-ir-names.h'
IR_FUNCTIONS_PATH = os.path.join(BE_PATH, IR_FUNCTIONS_FILE)
IR_NAMES_PATH = os.path.join(BE_PATH, IR_NAMES_FILE)
TMP_IR_FUNCTIONS_PATH = os.path.join(tempfile.gettempdir(), IR_FUNCTIONS_FILE)
TMP_IR_NAMES_PATH = os.path.join(tempfile.gettempdir(), IR_NAMES_FILE)

if not os.path.exists(BE_PATH):
  os.makedirs(BE_PATH)

if __name__ == "__main__":
  print "Generating IR description files"
  enums_file = open(TMP_IR_FUNCTIONS_PATH, 'w')
  enums_file.write(enums_preamble)

  names_file = open(TMP_IR_NAMES_PATH, 'w')
  names_file.write(names_preamble);

  idx = 0;
  enums_file.write("    FN_START = " + str(idx) + ",\n")
  for fn in ir_functions:
    enum = fn[0]
    fn_name = fn[1]
    enums_file.write("    " + enum + " = " + str(idx) + ",\n")
    names_file.write("  { \"" + fn_name + "\", IRFunction::" + enum + " },\n")
    idx = idx + 1;
  enums_file.write("    FN_END = " + str(idx) + "\n")

  enums_file.write(enums_epilogue)
  enums_file.close()

  names_file.write(names_epilogue)
  names_file.close()

  # Conditionally move files from tmp to BE.
  if options.noclean:
    move_if_different(TMP_IR_FUNCTIONS_PATH, IR_FUNCTIONS_PATH)
    move_if_different(TMP_IR_NAMES_PATH, IR_NAMES_PATH)
  else:
    shutil.move(TMP_IR_FUNCTIONS_PATH, IR_FUNCTIONS_PATH)
    shutil.move(TMP_IR_NAMES_PATH, IR_NAMES_PATH)
