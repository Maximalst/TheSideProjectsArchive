import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import base64

SAVE_DIR = "chat_logs"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

class StyledChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Messenger")
        self.root.geometry("900x550")
        self.root.configure(bg='#1e1e1e')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        self.contacts = {}
        self.chat_logs = {}
        self.current_chat = None
        self.unread = set()
        self.running = False
        self.dark_mode = True

        self.setup_ui()

    def styled_entry(self, parent, placeholder="", width=15):
        entry = tk.Entry(parent, width=width, bg='#2d2d2d', fg='#ffffff', insertbackground='white', bd=0)
        entry.insert(0, placeholder)
        return entry

    def styled_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#007acc", fg="white", activebackground="#005f99", bd=0, padx=10, pady=2)

    def setup_ui(self):
        top = tk.Frame(self.root, bg='#1e1e1e')
        top.pack(pady=5)

        tk.Label(top, text="Port:", fg="white", bg="#1e1e1e").grid(row=0, column=0)
        self.port_entry = self.styled_entry(top, "5005", width=8)
        self.port_entry.grid(row=0, column=1, padx=5)
        self.start_btn = self.styled_button(top, "Start", self.start_chat)
        self.start_btn.grid(row=0, column=2, padx=5)

        self.ip_btn = self.styled_button(top, "Eigene IP anzeigen", self.show_own_ip)
        self.ip_btn.grid(row=0, column=3, padx=5)

        contact_frame = tk.Frame(self.root, bg="#1e1e1e")
        contact_frame.pack(pady=5)

        self.contact_name = self.styled_entry(contact_frame, "Name")
        self.contact_name.grid(row=0, column=0, padx=3)
        self.contact_ip = self.styled_entry(contact_frame, "IP")
        self.contact_ip.grid(row=0, column=1, padx=3)
        self.contact_port = self.styled_entry(contact_frame, "Port")
        self.contact_port.grid(row=0, column=2, padx=3)

        self.add_btn = self.styled_button(contact_frame, "Hinzufügen", self.add_contact)
        self.add_btn.grid(row=0, column=3, padx=5)

        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.contact_list = tk.Listbox(main_frame, width=25, bg="#252526", fg="white", bd=0, selectbackground="#007acc")
        self.contact_list.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        self.contact_list.bind("<<ListboxSelect>>", self.switch_chat)

        chat_frame = tk.Frame(main_frame, bg="#1e1e1e")
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat_area = scrolledtext.ScrolledText(chat_frame, bg="#1e1e1e", fg="white", insertbackground='white', state='disabled', wrap=tk.WORD)
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.tag_config("green", foreground="lightgreen")
        self.chat_area.tag_config("blue", foreground="#4FC3F7")
        self.chat_area.tag_config("gray", foreground="gray")

        bottom = tk.Frame(chat_frame, bg="#1e1e1e")
        bottom.pack(fill=tk.X, pady=5)

        self.message_entry = self.styled_entry(bottom, width=50)
        self.message_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.send_message)

        self.file_btn = self.styled_button(bottom, "📎", self.send_file)
        self.file_btn.pack(side=tk.LEFT, padx=5)
        self.send_btn = self.styled_button(bottom, "Senden", self.send_message)
        self.send_btn.pack(side=tk.LEFT, padx=5)

        dark_toggle = self.styled_button(self.root, "🌙 Toggle Theme", self.toggle_theme)
        dark_toggle.pack(pady=5)

    def show_own_ip(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            messagebox.showinfo("Eigene IP-Adresse", f"Deine IP: {ip_address}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte IP nicht ermitteln: {e}")

    def toggle_theme(self):
        if self.dark_mode:
            self.root.configure(bg='white')
            self.chat_area.config(bg='white', fg='black')
            self.contact_list.config(bg='white', fg='black')
        else:
            self.root.configure(bg='#1e1e1e')
            self.chat_area.config(bg='#1e1e1e', fg='white')
            self.contact_list.config(bg='#252526', fg='white')
        self.dark_mode = not self.dark_mode

    def start_chat(self):
        try:
            port = int(self.port_entry.get())
            self.sock.bind(('', port))
            self.running = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
            self.start_btn.config(state='disabled')
            self.append_chat("🟢 Chat gestartet.", style="gray")
        except Exception as e:
            messagebox.showerror("Fehler", f"Portproblem: {e}")

    def add_contact(self):
        name = self.contact_name.get().strip()
        ip = self.contact_ip.get().strip()
        try:
            port = int(self.contact_port.get())
        except:
            messagebox.showerror("Fehler", "Ungültiger Port.")
            return

        if not name or not ip:
            return

        self.contacts[name] = (ip, port)
        self.chat_logs.setdefault(name, [])
        self.load_chat(name)
        self.contact_list.insert(tk.END, name)

    def switch_chat(self, event):
        selection = self.contact_list.curselection()
        if selection:
            name = self.contact_list.get(selection[0]).replace(" 🔔", "")
            self.current_chat = name
            self.display_chat(name)
            if name in self.unread:
                self.unread.remove(name)
                self.refresh_contact_list()

    def display_chat(self, name):
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        for msg, style in self.chat_logs.get(name, []):
            self.chat_area.insert(tk.END, msg + "\n", style)
        self.chat_area.config(state='disabled')

    def append_chat(self, msg, style="green", contact=None):
        target = contact or self.current_chat
        if not target:
            return
        self.chat_logs.setdefault(target, []).append((msg, style))
        if style == "blue":
            self.unread.add(target)
        if target == self.current_chat:
            self.chat_area.config(state='normal')
            self.chat_area.insert(tk.END, msg + "\n", style)
            self.chat_area.config(state='disabled')
            self.chat_area.see(tk.END)
        self.save_chat(target)
        self.refresh_contact_list()

    def refresh_contact_list(self):
        self.contact_list.delete(0, tk.END)
        for name in self.contacts:
            display = name + (" 🔔" if name in self.unread else "")
            self.contact_list.insert(tk.END, display)

    def send_message(self, event=None):
        msg = self.message_entry.get().strip()
        if msg and self.current_chat:
            self.message_entry.delete(0, tk.END)
            ip, port = self.contacts[self.current_chat]
            try:
                self.sock.sendto(msg.encode('utf-8'), (ip, port))
                self.append_chat("🟢 Du: " + msg, style="green")
            except:
                messagebox.showerror("Fehler", "Senden fehlgeschlagen.")

    def send_file(self):
        if not self.current_chat:
            return
        filepath = filedialog.askopenfilename()
        if filepath:
            with open(filepath, "rb") as f:
                data = base64.b64encode(f.read()).decode('utf-8')
                filename = os.path.basename(filepath)
                packet = f"[FILE]:{filename}:{data}"
                ip, port = self.contacts[self.current_chat]
                self.sock.sendto(packet.encode('utf-8'), (ip, port))
                self.append_chat(f"📤 Datei gesendet: {filename}", style="gray")

    def receive_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                msg = data.decode('utf-8')
                contact = self.get_contact_by_addr(addr)
                if not contact:
                    contact = f"{addr[0]}:{addr[1]}"
                    self.contacts[contact] = addr
                    self.chat_logs[contact] = []
                    self.contact_list.insert(tk.END, contact)

                if msg.startswith("[FILE]:"):
                    parts = msg.split(":", 2)
                    filename, filedata = parts[1], parts[2]
                    self.save_file(filename, filedata)
                    self.append_chat(f"📥 Datei empfangen: {filename}", style="gray", contact=contact)
                else:
                    self.append_chat(f"🔵 {contact}: {msg}", style="blue", contact=contact)
            except:
                continue

    def get_contact_by_addr(self, addr):
        for name, val in self.contacts.items():
            if val == addr:
                return name
        return None

    def save_file(self, filename, b64data):
        with open(f"received_{filename}", "wb") as f:
            f.write(base64.b64decode(b64data))

    def save_chat(self, name):
        filepath = os.path.join(SAVE_DIR, f"{name}.txt")
        with open(filepath, "w", encoding='utf-8') as f:
            for line, style in self.chat_logs.get(name, []):
                f.write(f"[{style}] {line}\n")

    def load_chat(self, name):
        filepath = os.path.join(SAVE_DIR, f"{name}.txt")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding='utf-8') as f:
                self.chat_logs[name] = []
                for line in f:
                    if line.startswith("[green]"):
                        msg = line[len("[green] "):].strip()
                        self.chat_logs[name].append((msg, "green"))
                    elif line.startswith("[blue]"):
                        msg = line[len("[blue] "):].strip()
                        self.chat_logs[name].append((msg, "blue"))
                    else:
                        msg = line.strip()
                        self.chat_logs[name].append((msg, "gray"))

# Start
if __name__ == "__main__":
    root = tk.Tk()
    app = StyledChatApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: [setattr(app, 'running', False), app.sock.close(), root.destroy()])
    root.mainloop()
