import tkinter as tk
from tkinter import ttk, messagebox
import threading
import customtkinter as ctk
from mailsync import GmailSync   # tumhari existing sync function
import os
def run_sync():
    try:
        log_box.insert(tk.END, "🔄 Sync started...\n")
        # start_sync()
        mailentry.get()
        syncgm = GmailSync(log_box)
        syncgm.USER_EMAIL = mailentry.get()
        syncgm.start_sync()
        log_box.insert(tk.END, "✅ Sync completed successfully!\n")
        messagebox.showinfo("Success", "Emails synced successfully!")
    except Exception as e:
        log_box.insert(tk.END, f"❌ Error: {str(e)}\n")
        messagebox.showerror("Error", str(e))

def start_sync_thread():
    t = threading.Thread(target=run_sync)
    t.start()

# ----------------- UI -----------------
root = tk.Tk()
root.configure(bg="#ffffff")
root.title("📩 Gmail Backup Tool")
root.geometry("500x400")

title = tk.Label(root, text="📩 Gmail Backup Tool", font=("Arial", 16, "bold"),bg='#fff')
title.pack(pady=10)

mailentry =ctk.CTkEntry(root, placeholder_text="Enter your Gmail address", width=300, height=40, border_width=2, corner_radius=10)
mailentry.pack(pady=10)
sync_btn = ctk.CTkButton(root, text="Sync Emails", command=start_sync_thread, width=200, height=50, fg_color="#4CAF50", text_color="white", hover_color="#45a049")
# sync_btn = tk.Button(root, text="Sync Emails", command=start_sync_thread, width=20, height=2, bg="green", fg="white")
sync_btn.pack(pady=10)

exit_btn = tk.Button(root, text="Exit", command=root.quit, width=20, height=2, bg="red", fg="white")
# exit_btn.pack(pady=10)

log_box = tk.Text(root, height=10, width=60)
log_box.pack(pady=10)
# try:
#     with open("auto.run", "r") as f:flag=f.read().strip()
#     if os.listdir("tokens"):
#         mailentry.insert(0, os.listdir("tokens")[0])
#     run_sync()
# except:flag=""

root.mainloop()
# ----------------- UI End -----------------
# ----------------- mailsync.py -----------------
