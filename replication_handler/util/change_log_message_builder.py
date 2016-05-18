# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

from data_pipeline.message import UpdateMessage
from pii_generator.components.pii_identifier import PIIIdentifier

from replication_handler.config import env_config
from replication_handler.config import source_database_config
from replication_handler.util.message_builder import MessageBuilder


log = logging.getLogger('replication_handler.parse_replication_stream')


class ChangeLogMessageBuilder(MessageBuilder):
    """ This class knows how to convert a data event into a respective message.

    Args:
      event(ReplicationHandlerEveent object): contains a create/update/delete data event and its position.
      schema_info(SchemaInfo object): contain topic/schema_id.
      resgiter_dry_run(boolean): whether a schema has to be registered for a message to be published.
    """
    def __init__(self, schema_info, event, position, register_dry_run=True):
        self.schema_info = schema_info
        self.event = event
        self.position = position
        self.register_dry_run = register_dry_run
        self.pii_identifier = PIIIdentifier(env_config.pii_yaml_path)

    def create_payload(self, data):
        payload_data = {"table_schema": self.event.schema,
                        "table_name": self.event.table,
                        "id": data['id'],
                        }
        return payload_data

    def build_message(self):
        upstream_position_info = {
            "position": self.position.to_dict(),
            "cluster_name": source_database_config.cluster_name,
            "database_name": self.event.schema,
            "table_name": self.event.table,
        }
        message_params = {
            "topic": str(self.schema_info.topic),
            "schema_id": self.schema_info.schema_id,
            "keys": tuple(self.schema_info.primary_keys),
            "payload_data": self.create_payload(self._get_values(self.event.row)),
            "upstream_position_info": upstream_position_info,
            "dry_run": self.register_dry_run,
            "contains_pii": self.pii_identifier.table_has_pii(
                database_name=self.event.schema,
                table_name=self.event.table
            ),
            "timestamp": self.event.timestamp,
            "meta": [self.position.transaction_id],
        }

        if self.event.message_type == UpdateMessage:
            message_params["previous_payload_data"] = self.create_payload(
                self.event.row["before_values"])

        return self.event.message_type(**message_params)
