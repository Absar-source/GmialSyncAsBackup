import os, re, json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.utils import parsedate_to_datetime
import base64, os, re
import email






class GmailSync():
    def __init__(self , log_box):
        
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.TOKENS_DIR = "tokens"
        self.USER_EMAIL = "absarqureshi88@gmail.com"  # e.g., "absaralam5432@gmail.com"
        self.log_box = log_box

    def start_sync(self):
        self.length = 0
        self.done = 0
        try:
            # If you already know the user's email, put it here:
            if self.USER_EMAIL:
                creds = self.load_creds_for(self.USER_EMAIL)
            else:
                # First time for this user:
                self.USER_EMAIL = self.login_once_and_save_tokens()
                creds = self.load_creds_for(self.USER_EMAIL)

            INDEX_FILE = f"emails/{self._safe(self.USER_EMAIL)}/index.json"
            
            # load already saved IDs
            if os.path.exists(INDEX_FILE):
                with open(INDEX_FILE, "r") as f:
                    saved_ids = set(json.load(f))
            else:
                saved_ids = set()
            new_ids = []

            # Test call: list 5 message snippets without re-login
            svc = build("gmail", "v1", credentials=creds)
            res = svc.users().messages().list(userId="me",maxResults=500).execute()
            msgs = res.get("messages", [])
            self.length = len(msgs)
            self.log_box.insert("end", f"📧 {self.length} emails found in the account.\n")

            for m in msgs:
                self.done += 1
                
                # skip if already saved
                msg_id = m["id"]
                if msg_id in saved_ids:
                    continue
                # skip if already saved
                full = svc.users().messages().get(userId="me", id=m["id"]).execute()
                headers = full["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender  = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                date_   = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
                reciever = next((h["value"] for h in headers if h["name"] == "To"), "Unknown")
                # parse date
                try:
                    parsed_date = parsedate_to_datetime(date_)
                    date_str = parsed_date.strftime("%Y-%m-%d_%H-%M-%S")
                except:
                    date_str = ""

                # safe names
                # in_path = os.path.join("emails", self._safe(self.USER_EMAIL))
                # os.makedirs(in_path, exist_ok=True)

                # sender_dir = os.path.join(in_path, self._safe(sender[:20]))
                sender_dir = f"emails/{self._safe(self.USER_EMAIL)}/{self._safe(sender)}"
                os.makedirs(sender_dir, exist_ok=True)



                subject_name = self._safe(subject)
                filename = f"{date_str}__{subject_name[:50]}.txt"
                filepath = os.path.join(sender_dir, filename)

                # save raw mail
                raw = svc.users().messages().get(userId="me", id=m["id"], format="raw").execute()
                raw_data = base64.urlsafe_b64decode(raw["raw"].encode("UTF-8"))
                self.formated_save_data(raw_data , headers, sender,date_str, subject, filepath)
                self.fetch_attachments(svc, self.USER_EMAIL, m["id"], sender_dir)
                self.log_box.insert("end", f"✅ ({self.done}/{self.length}) {subject} \n")
                self.log_box.see("end") 
                new_ids.append(msg_id)
            # update index.json
            if new_ids:
                saved_ids.update(new_ids)
                with open(INDEX_FILE, "w") as f:
                    json.dump(list(saved_ids), f)



        except Exception as e:
            print("❌", e)
            self.log_box.insert("end", f"❌ Error: {str(e)}\n")

    def _ensure_dir(self):
        os.makedirs(self.TOKENS_DIR, exist_ok=True)

    def _safe(self, text: str) -> str:
        # filename-safe (e.g., absar@example_com.json)
        # return re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
        bad_chars = r'\/:*?"<>|\\'
        return "".join(
            c if c.isalnum() or c in (" ", "_", "-") else "_"
            for c in text
        ).strip()
        # return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name).strip()
    
    def login_once_and_save_tokens(self) -> str:
        """
        1st time per user: Google login -> take email -> save tokens/<email>.json
        """
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
        # 'offline' + 'consent' ensure refresh_token mile (first time)
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        # get the user's Gmail address
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email_addr = profile["emailAddress"]

        self._ensure_dir()
        path = os.path.join(self.TOKENS_DIR, f"{self._safe(email_addr)}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"✅ Saved credentials for {email_addr} -> {path}")
        self.log_box.insert("end", f"✅ Saved credentials for {email_addr} -> {path}\n")
        return email_addr
    
    def load_creds_for(self, email_addr: str) -> Credentials:
        """
        Later runs: load tokens, auto-refresh if expired, re-save.
        """
        path = os.path.join(self.TOKENS_DIR, f"{self._safe(email_addr)}.json")
        self.log_box.insert("end", f"Loading saved tokens for {email_addr} from {path}\n")
        if not os.path.exists(path):
            self.log_box.insert("end", f"❌ No saved tokens for {email_addr}. now login with account  first.\n")
            self.login_once_and_save_tokens()
            # raise FileNotFoundError(f"No saved tokens for {email_addr}. Run login_once_and_save_tokens() first.")
            # raise FileNotFoundError(f"now sync with {email_addr}. Run login_once_and_save_tokens() first.")

        creds = Credentials.from_authorized_user_file(path, self.SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # persist refreshed access token & new expiry
                with open(path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            else:
                # No refresh_token? Do first-time login again with prompt='consent'
                self.log_box.insert("end", f"❌ Saved creds invalid and no refresh_token present. Run login_once_and_save_tokens().\n")
                raise RuntimeError("Saved creds invalid and no refresh_token present. Run login_once_and_save_tokens().")

        return creds
        
    def fetch_attachments(self,service, user_email, msg_id, save_dir):
        message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        parts = message.get("payload", {}).get("parts", [])
        # print(f"payload parts: {json.dumps(parts, indent=2)} , message : {message}")
        for part in parts:
            filename = part.get("filename")
            body = part.get("body", {})
            if filename and "attachmentId" in body:
                print(f"Found attachment: {filename}")
                att_id = body["attachmentId"]
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()

                file_data = base64.urlsafe_b64decode(att["data"].encode("UTF-8"))
                print(f"Saving attachment to {save_dir}/{filename}")
                self.log_box.insert("end", f"📎 Saving attachment to {save_dir}/{filename}\n")
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(file_data)

                print(f"📎 Attachment saved: {filepath}")
    def formated_save_data(self,raw_data , headers, sender,date_, subject, filepath):
            
        # parse into email object
        msg_obj = email.message_from_bytes(raw_data)

        # extract plain text body
        body = ""
        if msg_obj.is_multipart():
            for part in msg_obj.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg_obj.get_payload(decode=True).decode(errors="ignore")

        # formatted content
        formatted = f"""
        From: {sender}
        To: {next((h["value"] for h in headers if h["name"] == "To"), "")}
        Date: {date_}
        Subject: {subject}

        {"-"*50}
        {body}
        """

        # save as readable text
        # filepath = os.path.join(sender_dir, f"{date_str}__{subject_name}.txt")
        print(f"Saving email to {filepath}")
        self.log_box.insert("end", f"💾 Saving email to {filepath}\n")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted)

