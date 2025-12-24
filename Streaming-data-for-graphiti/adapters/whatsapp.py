from adapters.base import BaseAdapter
from schemas import StreamEvent, SourceType

class WhatsAppAdapter(BaseAdapter):

    def parse(self, payload: dict):
        for record in payload:
            for entry in record["entry"]:
                stream_id = entry["id"]

                for change in entry["changes"]:
                    value = change["value"]

                    contacts = {
                        c["wa_id"]: c["profile"]["name"]
                        for c in value.get("contacts", [])
                    }

                    for msg in value.get("messages", []):
                        yield StreamEvent(
                            source=SourceType.whatsapp,
                            stream_id=stream_id,
                            event_id=msg["id"],
                            actor_id=msg["from"],
                            actor_name=contacts.get(msg["from"]),
                            timestamp=int(msg["timestamp"]),
                            content=msg["text"]["body"],
                            parent_event_id=msg.get("parent_message_id"),
                            raw_payload=msg
                        )
