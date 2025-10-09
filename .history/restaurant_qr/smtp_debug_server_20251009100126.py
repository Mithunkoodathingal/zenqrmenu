# smtp_debug_server.py
# Run: python smtp_debug_server.py
from aiosmtpd.controller import Controller
from email.parser import BytesParser
import sys

class PrintHandler:
    async def handle_DATA(self, server, session, envelope):
        # envelope.content is bytes
        print("\n\n=== Received message ===")
        try:
            msg = BytesParser().parsebytes(envelope.content)
            print("From:", envelope.mail_from)
            print("To:", envelope.rcpt_tos)
            print("Subject:", msg.get('Subject'))
            print("\n--- Full headers ---")
            for k,v in msg.items():
                print(f"{k}: {v}")
            print("\n--- Body (first 1000 chars) ---")
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    text = payload.decode('utf-8', errors='replace')
                except Exception:
                    text = str(payload)[:1000]
                print(text[:1000])
            else:
                print("(no payload)")
        except Exception as e:
            print("Error parsing message:", e, file=sys.stderr)
        print("=== End message ===\n\n")
        return '250 Message accepted for delivery'

if __name__ == "__main__":
    handler = PrintHandler()
    controller = Controller(handler, hostname='127.0.0.1', port=1025)
    controller.start()
    print("SMTP debug server running on 127.0.0.1:1025 — press Ctrl+C to stop")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        controller.stop()
        print("SMTP debug server stopped")
