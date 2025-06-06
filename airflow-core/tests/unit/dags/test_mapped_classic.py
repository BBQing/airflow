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
from __future__ import annotations

import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import task


@task
def make_arg_lists():
    return [[1], [2], [{"a": "b"}]]


def consumer(value):
    print(repr(value))


with DAG(dag_id="test_mapped_classic", schedule=None, start_date=datetime.datetime(2022, 1, 1)) as dag:
    PythonOperator.partial(task_id="consumer", python_callable=consumer).expand(op_args=make_arg_lists())
    PythonOperator.partial(task_id="consumer_literal", python_callable=consumer).expand(
        op_args=[[1], [2], [3]],
    )
