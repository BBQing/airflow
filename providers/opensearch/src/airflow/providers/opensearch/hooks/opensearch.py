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
from __future__ import annotations

import json
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypedDict

from opensearchpy import OpenSearch, RequestsHttpConnection

if TYPE_CHECKING:
    from opensearchpy import Connection as OpenSearchConnectionClass

from airflow.exceptions import AirflowException
from airflow.providers.opensearch.version_compat import BaseHook
from airflow.utils.strings import to_boolean


class OpenSearchClientArguments(TypedDict, total=False):
    """Typed arguments to the open search client."""

    hosts: str | list[dict] | None
    use_ssl: bool
    verify_certs: bool
    connection_class: type[OpenSearchConnectionClass] | None
    http_auth: tuple[str, str]


class OpenSearchHook(BaseHook):
    """
    Provide a thin wrapper around the OpenSearch client.

    :param open_search_conn_id: Connection to use with OpenSearch
    :param log_query: Whether to log the query used for OpenSearch
    """

    conn_name_attr = "opensearch_conn_id"
    default_conn_name = "opensearch_default"
    conn_type = "opensearch"
    hook_name = "OpenSearch Hook"

    def __init__(
        self,
        open_search_conn_id: str,
        log_query: bool,
        open_search_conn_class: type[OpenSearchConnectionClass] | None = RequestsHttpConnection,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.conn_id = open_search_conn_id
        self.log_query = log_query

        self.use_ssl = to_boolean(str(self.conn.extra_dejson.get("use_ssl", False)))
        self.verify_certs = to_boolean(str(self.conn.extra_dejson.get("verify_certs", False)))
        self.connection_class = open_search_conn_class
        self.__SERVICE = "es"

    @cached_property
    def conn(self):
        return self.get_connection(self.conn_id)

    @cached_property
    def client(self) -> OpenSearch:
        """This function is intended for Operators that forward high level client objects."""
        client_args: OpenSearchClientArguments = dict(
            hosts=[{"host": self.conn.host, "port": self.conn.port}],
            use_ssl=self.use_ssl,
            verify_certs=self.verify_certs,
            connection_class=self.connection_class,
        )
        if self.conn.login and self.conn.password:
            client_args["http_auth"] = (self.conn.login, self.conn.password)
        client = OpenSearch(**client_args)
        return client

    def search(self, query: dict, index_name: str, **kwargs: Any) -> Any:
        """
        Run a search query against the connected OpenSearch cluster.

        :param query: The query for the search against OpenSearch.
        :param index_name: The name of the index to search against
        """
        if self.log_query:
            self.log.info("Searching %s with Query: %s", index_name, query)
        return self.client.search(body=query, index=index_name, **kwargs)

    def index(self, document: dict, index_name: str, doc_id: int, **kwargs: Any) -> Any:
        """
        Index a document on OpenSearch.

        :param document: A dictionary representation of the document
        :param index_name: the name of the index that this document will be associated with
        :param doc_id: the numerical identifier that will be used to identify the document on the index.
        """
        return self.client.index(index=index_name, id=doc_id, body=document, **kwargs)

    def delete(self, index_name: str, query: dict | None = None, doc_id: int | None = None) -> Any:
        """
        Delete from an index by either a query or by the document id.

        :param index_name: the name of the index to delete from
        :param query: If deleting by query a dict representation of the query to run to
            identify documents to delete.
        :param doc_id: The identifier of the document to delete.
        """
        if query is not None:
            if self.log_query:
                self.log.info("Deleting from %s using Query: %s", index_name, query)
            return self.client.delete_by_query(index=index_name, body=query)
        if doc_id is not None:
            return self.client.delete(index=index_name, id=doc_id)
        raise AirflowException(
            "To delete a document you must include one of either a query or a document id."
        )

    @classmethod
    def get_ui_field_behaviour(cls) -> dict[str, Any]:
        """Return custom UI field behaviour for OpenSearch Connection."""
        return {
            "hidden_fields": ["schema"],
            "relabeling": {
                "extra": "OpenSearch Configuration",
            },
            "placeholders": {
                "extra": json.dumps(
                    {"use_ssl": True, "verify_certs": True},
                    indent=2,
                ),
            },
        }
