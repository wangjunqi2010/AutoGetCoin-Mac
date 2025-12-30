import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Menu, Toplevel
import requests
import time
import random
import urllib3
import threading
import os
import sys

# 禁用 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ================= 资源路径处理 =================
def resource_path(relative_path):
    """ 获取资源绝对路径，兼容 Dev 和 PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ================= 主程序类 =================
class AutoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("全自动体力获取助手 v1.0")
        self.root.geometry("900x750")

        # === 主题配色 ===
        self.themes = {
            "dark": {
                "bg_color": "#2b2b2b", "fg_color": "#ffffff", "input_bg": "#3c3f41",
                "input_fg": "#ffffff", "insert_bg": "white", "placeholder": "#808080",
                "highlight": "#e6db74", "btn_bg": "#4caf50", "btn_fg": "white",
                "log_bg": "#1e1e1e", "log_fg": "#dcdcdc", "log_time": "#569cd6",
                "log_success": "#4caf50", "log_warn": "#ff9800", "log_error": "#f44336",
                "popup_bg": "#2b2b2b", "popup_fg": "#ffffff"
            },
            "light": {
                "bg_color": "#f5f5f5", "fg_color": "#333333", "input_bg": "#ffffff",
                "input_fg": "#000000", "insert_bg": "black", "placeholder": "#a9a9a9",
                "highlight": "#2e7d32", "btn_bg": "#4caf50", "btn_fg": "white",
                "log_bg": "#ffffff", "log_fg": "#333333", "log_time": "#0066cc",
                "log_success": "#2e7d32", "log_warn": "#f57c00", "log_error": "#d32f2f",
                "popup_bg": "#ffffff", "popup_fg": "#333333"
            }
        }

        self.current_theme = "light"
        self.colors = self.themes["light"]
        self.is_running = False
        self.thread = None
        self.cookie_placeholder = "请在此处粘贴 Cookie (rec_token=...)"
        self.img_ref = None

        self.create_menu()
        self.create_widgets()
        self.apply_theme("light")

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        theme_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🎨 主题切换", menu=theme_menu)
        theme_menu.add_radiobutton(label="浅色模式", command=lambda: self.apply_theme("light"))
        theme_menu.add_radiobutton(label="深色模式", command=lambda: self.apply_theme("dark"))
        theme_menu.add_separator()
        theme_menu.add_command(label="关于",
                               command=lambda: messagebox.showinfo("关于", "全自动助手 v1.0\nMade with Python Tkinter"))

    def create_widgets(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10), ipadx=5)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)

        # [Cookie]
        self.cookie_frame = ttk.LabelFrame(left_panel, text=" 身份凭证 (Cookie) ")
        self.cookie_frame.pack(fill="x", pady=5)

        help_header = ttk.Frame(self.cookie_frame)
        help_header.pack(fill="x", padx=5, pady=(5, 0))
        ttk.Label(help_header, text="请粘贴完整的 Cookie 内容:").pack(side="left")
        self.btn_help = tk.Button(help_header, text="❓ 如何获取 Cookie?", command=self.show_cookie_help,
                                  font=("微软雅黑", 9), bd=1, relief="raised", cursor="hand2")
        self.btn_help.pack(side="right")

        self.txt_cookie = tk.Text(self.cookie_frame, height=8, width=40, borderwidth=1, relief="solid",
                                  font=("Consolas", 9))
        self.txt_cookie.pack(fill="x", padx=5, pady=5)
        self.txt_cookie.bind("<FocusIn>", self.on_cookie_focus_in)
        self.txt_cookie.bind("<FocusOut>", self.on_cookie_focus_out)
        self.on_cookie_focus_out(None)

        # [Params]
        self.param_frame = ttk.LabelFrame(left_panel, text=" 运行参数 ")
        self.param_frame.pack(fill="x", pady=5)

        # 1. 随机间隔
        time_grid = ttk.Frame(self.param_frame)
        time_grid.pack(fill="x", padx=5, pady=5)
        ttk.Label(time_grid, text="随机间隔(秒):").pack(side="left")
        self.var_min_time = tk.IntVar(value=5)
        self.var_max_time = tk.IntVar(value=10)
        self.spin_min = tk.Spinbox(time_grid, from_=1, to=60, textvariable=self.var_min_time, width=5)
        self.spin_min.pack(side="left", padx=5)
        ttk.Label(time_grid, text="~").pack(side="left")
        self.spin_max = tk.Spinbox(time_grid, from_=1, to=60, textvariable=self.var_max_time, width=5)
        self.spin_max.pack(side="left", padx=5)

        # 🟢 2. 新增：跳过置顶设置
        skip_grid = ttk.Frame(self.param_frame)
        skip_grid.pack(fill="x", padx=5, pady=5)
        ttk.Label(skip_grid, text="跳过前N个贴:").pack(side="left")
        self.var_skip_count = tk.IntVar(value=10)  # 默认跳过10个
        self.entry_skip = tk.Entry(skip_grid, textvariable=self.var_skip_count, width=10)
        self.entry_skip.pack(side="left", padx=5)
        ttk.Label(skip_grid, text="(置顶/公告)", font=("微软雅黑", 8), foreground="gray").pack(side="left")

        # 3. 目标数量
        target_grid = ttk.Frame(self.param_frame)
        target_grid.pack(fill="x", padx=5, pady=5)
        ttk.Label(target_grid, text="点赞目标数:").grid(row=0, column=0, sticky="w", pady=2)
        self.var_target_likes = tk.IntVar(value=200)
        self.entry_target_like = tk.Entry(target_grid, textvariable=self.var_target_likes, width=10)
        self.entry_target_like.grid(row=0, column=1, padx=5)

        ttk.Label(target_grid, text="评论目标数:").grid(row=1, column=0, sticky="w", pady=2)
        self.var_target_comments = tk.IntVar(value=20)
        self.entry_target_comment = tk.Entry(target_grid, textvariable=self.var_target_comments, width=10)
        self.entry_target_comment.grid(row=1, column=1, padx=5)

        # [Comment]
        self.comment_frame = ttk.LabelFrame(left_panel, text=" 评论内容设置 ")
        self.comment_frame.pack(fill="x", pady=5)
        ttk.Label(self.comment_frame, text="自动发送的内容:").pack(anchor="w", padx=5, pady=2)
        self.var_comment_text = tk.StringVar(value="666")
        self.entry_comment = tk.Entry(self.comment_frame, textvariable=self.var_comment_text)
        self.entry_comment.pack(fill="x", padx=5, pady=5)
        self.lbl_tip = ttk.Label(self.comment_frame, text="* 程序会自动转换格式，直接写字即可", font=("微软雅黑", 8))
        self.lbl_tip.pack(anchor="w", padx=5)

        # [Control]
        self.ctrl_frame = ttk.LabelFrame(left_panel, text=" 任务控制 ")
        self.ctrl_frame.pack(fill="x", pady=10)
        self.var_mode = tk.StringVar(value="like")
        ttk.Radiobutton(self.ctrl_frame, text="执行【自动点赞】", variable=self.var_mode, value="like").pack(anchor="w",
                                                                                                           padx=10,
                                                                                                           pady=2)
        ttk.Radiobutton(self.ctrl_frame, text="执行【自动评论】", variable=self.var_mode, value="comment").pack(
            anchor="w", padx=10, pady=2)
        self.btn_start = tk.Button(self.ctrl_frame, text="开始运行", command=self.start_thread,
                                   font=("微软雅黑", 12, "bold"), relief="flat")
        self.btn_start.pack(fill="x", padx=10, pady=10)
        self.btn_stop = tk.Button(self.ctrl_frame, text="停止任务", command=self.stop_task, font=("微软雅黑", 10),
                                  relief="flat", state="disabled")
        self.btn_stop.pack(fill="x", padx=10, pady=(0, 10))

        # [Log]
        ttk.Label(right_panel, text=" 执行日志", font=("微软雅黑", 10, "bold")).pack(anchor="w", pady=(5, 0))
        self.log_area = scrolledtext.ScrolledText(right_panel, font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, pady=5)

    def show_cookie_help(self):
        c = self.colors
        top = Toplevel(self.root)
        top.title("Cookie 获取教程")
        top.geometry("750x600")
        top.configure(bg=c["popup_bg"])
        st = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("微软雅黑", 10), bg=c["popup_bg"], fg=c["popup_fg"],
                                       borderwidth=0, relief="flat", padx=20, pady=20)
        st.pack(fill="both", expand=True)

        guide_text = (
            "【步骤说明】\n1. 电脑端打开新生人首页。\n2. 点击快捷键Ctrl + Alt + Shift + D，提示“调试模式已开启”。\n"
            "3. 右键 → ShowDevTools，即可打开浏览器开发者工具。\n4. 点击 Network，随便点击一个帖子，下面 Name 栏会出现数据，"
            "点击不同的数据，在右边的 Headers 中 找到Request Headers，获取其 Cookie 的值。\n5. 选中其 Cookie 的值，粘贴到本软件输入框中。\n\n👇 参考图示 👇"
        )
        st.insert(tk.END, guide_text)

        try:
            img_path = resource_path("cookie_guide.png")
            if os.path.exists(img_path):
                self.img_ref = tk.PhotoImage(file=img_path)
                st.image_create(tk.END, image=self.img_ref)
            else:
                st.insert(tk.END, "\n[未找到图片]\n请确保 cookie_guide.png 存在。")
        except Exception as e:
            st.insert(tk.END, f"\n[图片加载失败]\n错误: {e}")
        st.configure(state="disabled")

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        c = self.themes[theme_name]
        self.colors = c
        self.root.configure(bg=c["bg_color"])
        self.style.configure("TFrame", background=c["bg_color"])
        self.style.configure("TLabel", background=c["bg_color"], foreground=c["fg_color"])
        self.style.configure("TRadiobutton", background=c["bg_color"], foreground=c["fg_color"])
        self.style.configure("TLabelframe", background=c["bg_color"], foreground=c["fg_color"])
        self.style.configure("TLabelframe.Label", background=c["bg_color"], foreground=c["highlight"])

        tk_widgets = [self.txt_cookie, self.spin_min, self.spin_max, self.entry_target_like, self.entry_target_comment,
                      self.entry_comment, self.entry_skip]
        for w in tk_widgets: w.config(bg=c["input_bg"], fg=c["input_fg"], insertbackground=c["insert_bg"])

        self.btn_start.config(bg=c["btn_bg"], fg=c["btn_fg"], activebackground="#45a049")
        self.btn_stop.config(bg="#f44336", fg="white", activebackground="#d32f2f")
        self.btn_help.config(bg=c["input_bg"], fg=c["highlight"], activebackground=c["bg_color"])
        self.log_area.config(bg=c["log_bg"], fg=c["log_fg"], insertbackground=c["insert_bg"])

        for tag, color in [("INFO", c["log_fg"]), ("SUCCESS", c["log_success"]), ("WARN", c["log_warn"]),
                           ("ERROR", c["log_error"]), ("TIME", c["log_time"])]:
            self.log_area.tag_config(tag, foreground=color)

        current = self.txt_cookie.get("1.0", "end-1c").strip()
        self.txt_cookie.config(
            fg=c["placeholder"] if (not current or current == self.cookie_placeholder) else c["highlight"])
        self.lbl_tip.config(foreground="gray")

    def on_cookie_focus_in(self, event):
        if self.txt_cookie.get("1.0", "end-1c") == self.cookie_placeholder:
            self.txt_cookie.delete("1.0", "end")
            self.txt_cookie.config(fg=self.colors["highlight"])

    def on_cookie_focus_out(self, event):
        if not self.txt_cookie.get("1.0", "end-1c").strip():
            self.txt_cookie.insert("1.0", self.cookie_placeholder)
            self.txt_cookie.config(fg=self.colors["placeholder"])

    def log(self, msg, level="INFO"):
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] ", "TIME")
        self.log_area.insert(tk.END, f"{msg}\n", level)
        self.log_area.see(tk.END)

    def start_thread(self):
        if self.is_running: return
        raw = self.txt_cookie.get("1.0", "end-1c").strip()
        if not raw or raw == self.cookie_placeholder:
            messagebox.showwarning("提示", "Cookies 不能为空！")
            return

        self.cookie_val = raw
        user_cmt = self.var_comment_text.get().strip() or "666"
        self.config = {
            "min_time": self.var_min_time.get(), "max_time": self.var_max_time.get(),
            "target_likes": self.var_target_likes.get(), "target_comments": self.var_target_comments.get(),
            "comment_text": user_cmt, "mode": self.var_mode.get(),
            # 🟢 记录跳过数量
            "skip_count": self.var_skip_count.get()
        }
        self.is_running = True
        self.btn_start.config(state="disabled", text="运行中...")
        self.btn_stop.config(state="normal")
        self.log("🚀 任务已启动...", "SUCCESS")
        self.thread = threading.Thread(target=self.run_task)
        self.thread.daemon = True
        self.thread.start()

    def stop_task(self):
        if self.is_running:
            self.is_running = False
            self.log("🛑 用户停止...", "WARN")
            self.btn_start.config(state="normal", text="开始运行")
            self.btn_stop.config(state="disabled")

    def run_task(self):
        LIST_URL = "https://m.vrenke.com/v1/sub/dynamic/infoflow/latest"
        LIKE_URL = "https://m.vrenke.com/v1/sub/mobileDynamic/savePraise"
        COMMENT_URL = "https://m.vrenke.com/v1/sub/interact/comment"
        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.101 Safari/537.36 Language/zh ColorScheme/Light wxwork/5.0.3 (MicroMessenger/6.2) WindowsWechat MailPlugin_Electron WeMail embeddisk wwmver/3.26.503.665 noMediaCs/false",
            "Content-Type": "application/json;charset=UTF-8", "Cookie": self.cookie_val,
            "Origin": "https://m.vrenke.com", "Referer": "https://m.vrenke.com/pc/index.html"
        }

        mode = self.config["mode"]
        target = self.config["target_likes"] if mode == "like" else self.config["target_comments"]

        # 🟢 获取需要跳过的总数
        total_skip_needed = self.config["skip_count"]
        # 🟢 已经跳过的数量
        skipped_so_far = 0

        if total_skip_needed > 0:
            self.log(f"⚠️ 已配置跳过前 {total_skip_needed} 个置顶/公告帖子...", "WARN")

        count = 0
        page = 1

        while count < target and self.is_running:
            self.log(f"📡 拉取第 {page} 页...", "INFO")
            try:
                r = requests.post(LIST_URL, headers=HEADERS, json={"pageNum": page, "pageSize": 10}, verify=False,
                                  timeout=10)
                items = []
                if r.status_code == 200:
                    d = r.json()
                    items = d.get("data", {}).get("list", []) or d.get("result", {}).get("returnObject", {}).get("list",
                                                                                                                 [])

                if not items:
                    self.log(f"⚠️ 第 {page} 页无数据，翻页...", "WARN")
                    page += 1;
                    time.sleep(2)
                    if page > 30: break
                    continue

                self.log(f"📄 获取 {len(items)} 条数据...", "INFO")

                for item in items:
                    if count >= target or not self.is_running: break

                    # 🟢 核心跳过逻辑
                    if skipped_so_far < total_skip_needed:
                        skipped_so_far += 1
                        # 仅在刚开始跳过时打印一下日志，避免刷屏
                        # self.log(f"   ↪️ 跳过置顶贴 [{skipped_so_far}/{total_skip_needed}]", "INFO")
                        continue

                    did = item.get("dynamicId")

                    if mode == "like":
                        inter = item.get("interact", {})
                        if (inter.get("isPraise") == "N" or inter.get("praised") is False) and did:
                            try:
                                r2 = requests.post(LIKE_URL, headers=HEADERS, params={"id": did}, verify=False,
                                                   timeout=10)
                                if r2.status_code == 200:
                                    res = r2.json()
                                    if not res.get("result", {}).get("errorMessages"):
                                        count += 1
                                        self.log(f"[{count}/{target}] ✅ 帖子ID {did} 点赞成功", "SUCCESS")
                                    else:
                                        self.log(f"⚠️ 帖子ID {did} 已赞过", "INFO")
                            except Exception as e:
                                self.log(f"💥 异常: {e}", "ERROR")
                            sleep_t = random.uniform(self.config["min_time"], self.config["max_time"])
                            self.log(f"⏳ 随机休息 {sleep_t:.1f} 秒...", "INFO")
                            time.sleep(sleep_t)

                    elif mode == "comment":
                        if did:
                            try:
                                c_load = {
                                    "dynamicId": did, "commentType": "dynamic", "parentId": None, "id": did,
                                    "dynamicType": "ShareHtml", "bizId": None, "type": "comment",
                                    "content": f"<div>{self.config['comment_text']}</div>", "isAnonymity": "N"
                                }
                                r3 = requests.post(COMMENT_URL, headers=HEADERS, json=c_load, verify=False, timeout=10)
                                if r3.status_code == 200 and (
                                        r3.json().get("succ") is True or r3.json().get("code") == "0000"):
                                    count += 1
                                    self.log(f"[{count}/{target}] 💬 帖子ID {did} 评论成功", "SUCCESS")
                                else:
                                    self.log(f"❌ 帖子ID {did} 失败", "ERROR")
                            except Exception as e:
                                self.log(f"💥 异常: {e}", "ERROR")
                            sleep_t = random.uniform(self.config["min_time"], self.config["max_time"])
                            self.log(f"⏳ 随机休息 {sleep_t:.1f} 秒...", "INFO")
                            time.sleep(sleep_t)

                page += 1
                self.log("------------- 翻页 -------------", "INFO")
            except Exception as e:
                self.log(f"❌ 严重错误: {e}", "ERROR")
                time.sleep(5)

        self.is_running = False
        self.btn_start.config(state="normal", text="开始运行")
        self.btn_stop.config(state="disabled")
        self.log(f"🏁 任务结束，共成功 {count} 次", "SUCCESS")


# ================= 🟢 免责声明入口 =================
if __name__ == "__main__":
    # 1. 创建临时的 root 窗口用于弹窗（不显示主界面）
    temp_root = tk.Tk()
    temp_root.withdraw()  # 隐藏主窗口

    # 2. 准备免责声明文案
    disclaimer_text = (
        "【免责声明】\n\n"
        "1. 本软件仅供技术交流与学习使用，完全免费。\n"
        "2. 请勿将本软件用于任何商业用途或非法行为。\n"
        "3. 作者不对使用本软件产生的任何后果负责（包括但不限于账号封禁、数据异常等）。\n"
        "4. 请在下载体验后 24 小时内删除本软件。\n"
        "5. 点击“同意”即代表您已阅读并接受上述条款。"
    )

    # 3. 弹出确认框
    user_agreed = messagebox.askyesno("用户协议与免责声明", disclaimer_text, icon='warning')

    # 4. 根据用户选择决定是否启动
    if user_agreed:
        temp_root.destroy()  # 销毁临时窗口

        # 启动主程序
        root = tk.Tk()
        app = AutoBotGUI(root)
        root.mainloop()
    else:
        temp_root.destroy()

        sys.exit()  # 用户拒绝，直接退出
