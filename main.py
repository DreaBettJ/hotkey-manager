#!/usr/bin/env python3
"""
Hotkey Manager - Ubuntu 快捷键管理工具
功能：
1. GitHub 仓库创建和提交
2. 快捷键与当前活动窗口关联
3. 支持添加快捷键和说明
4. 快捷键搜索
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import subprocess
import keyboard
import pyperclip
import requests
from datetime import datetime
import threading
import sys

# 配置文件路径
CONFIG_FILE = os.path.expanduser("~/.config/hotkey_manager/data.json")
HOTKEY_FILE = os.path.expanduser("~/.config/hotkey_manager/hotkeys.json")

class HotkeyManager:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Hotkey Manager")
        self.root.geometry("900x600")
        
        # 数据
        self.hotkeys = self.load_hotkeys()
        self.github_token = self.load_github_token()
        
        # 当前活动窗口
        self.current_window = "Unknown"
        self.window_monitor_thread = None
        self.running = True
        
        # UI
        self.setup_ui()
        self.setup_hotkeys()
        self.start_window_monitor()
        
        # 注册全局快捷键
        self.register_global_hotkeys()
    
    def setup_ui(self):
        """设置主界面"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(fill=tk.X)
        
        ttk.Button(toolbar, text="➕ 添加快捷键", command=self.add_hotkey).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📝 编辑", command=self.edit_hotkey).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ 删除", command=self.delete_hotkey).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔍 搜索", command=self.toggle_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔗 GitHub", command=self.github_menu).pack(side=tk.LEFT, padx=20)
        ttk.Button(toolbar, text="⚙️ 设置", command=self.settings).pack(side=tk.RIGHT, padx=5)
        
        # 当前窗口显示
        self.window_label = ttk.Label(self.root, text="当前窗口: Unknown", foreground="blue")
        self.window_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 搜索框（默认隐藏）
        self.search_frame = ttk.Frame(self.root)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_hotkeys)
        search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(self.search_frame, text="清除", command=self.clear_search).pack(side=tk.RIGHT, padx=10)
        self.search_frame.pack(fill=tk.X)
        self.search_frame.pack_forget()
        
        # 快捷键列表
        columns = ("window", "hotkey", "description", "action")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("window", text="窗口")
        self.tree.heading("hotkey", text="快捷键")
        self.tree.heading("description", text="说明")
        self.tree.heading("action", text="执行动作")
        
        self.tree.column("window", width=150)
        self.tree.column("hotkey", width=120)
        self.tree.column("description", width=300)
        self.tree.column("action", width=200)
        
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪 | 快捷键: Ctrl+Alt+H 显示主窗口")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 双击执行
        self.tree.bind("<Double-1>", self.execute_hotkey)
        
        self.refresh_list()
    
    def setup_hotkeys(self):
        """注册系统级快捷键"""
        keyboard.add_hotkey('ctrl+alt+h', self.toggle_window)
        keyboard.add_hotkey('ctrl+alt+s', self.save_hotkeys)
    
    def start_window_monitor(self):
        """启动窗口监控"""
        def monitor():
            import Xlib
            from Xlib import X, display
            
            d = display.Display()
            root = d.screen().root
            
            while self.running:
                try:
                    active_window = root.get_property(
                        d.intern_atom('_NET_ACTIVE_WINDOW'),
                        Xlib.X.AnyPropertyType,
                        0, 1024
                    ).value[0]
                    
                    window = d.create_resource_object('window', active_window)
                    window.map()
                    
                    window_name = window.get_wm_name()
                    if window_name:
                        self.current_window = window_name.split()[0] if ' ' in window_name else window_name
                        
                except:
                    pass
                    
                self.root.after(0, self.update_window_label)
                import time
                time.sleep(1)
        
        self.window_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.window_monitor_thread.start()
    
    def update_window_label(self):
        """更新当前窗口标签"""
        self.window_label.config(text=f"当前窗口: {self.current_window}")
    
    def load_hotkeys(self):
        """加载快捷键数据"""
        if os.path.exists(HOTKEY_FILE):
            try:
                with open(HOTKEY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_hotkeys(self):
        """保存快捷键数据"""
        os.makedirs(os.path.dirname(HOTKEY_FILE), exist_ok=True)
        with open(HOTKEY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.hotkeys, f, ensure_ascii=False, indent=2)
        self.status_var.set(f"已保存 {len(self.hotkeys)} 个快捷键 | {datetime.now().strftime('%H:%M:%S')}")
    
    def refresh_list(self, filtered_list=None):
        """刷新列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        items = filtered_list if filtered_list else self.hotkeys
        for hk in items:
            self.tree.insert("", tk.END, values=(
                hk.get('window', ''),
                hk.get('hotkey', ''),
                hk.get('description', ''),
                hk.get('action', '')
            ))
    
    def filter_hotkeys(self, *args):
        """搜索过滤"""
        keyword = self.search_var.get().lower()
        if not keyword:
            self.refresh_list()
            return
        
        filtered = [hk for hk in self.hotkeys 
                   if keyword in hk.get('hotkey', '').lower() 
                   or keyword in hk.get('description', '').lower()
                   or keyword in hk.get('window', '').lower()]
        self.refresh_list(filtered)
    
    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
        self.search_frame.pack_forget()
    
    def toggle_search(self):
        """切换搜索框显示"""
        if self.search_frame.winfo_ismapped():
            self.search_frame.pack_forget()
        else:
            self.search_frame.pack(fill=tk.X, pady=5)
            self.search_frame.lift()
    
    def add_hotkey(self):
        """添加快捷键"""
        dialog = AddHotkeyDialog(self.root, self.current_window)
        if dialog.result:
            self.hotkeys.append(dialog.result)
            self.save_hotkeys()
            self.refresh_list()
            self.register_global_hotkeys()
    
    def edit_hotkey(self):
        """编辑快捷键"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择一个快捷键")
            return
        
        idx = self.tree.index(selected[0])
        old_hk = self.hotkeys[idx]
        
        dialog = EditHotkeyDialog(self.root, old_hk)
        if dialog.result:
            self.hotkeys[idx] = dialog.result
            self.save_hotkeys()
            self.refresh_list()
            self.register_global_hotkeys()
    
    def delete_hotkey(self):
        """删除快捷键"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择一个快捷键")
            return
        
        if messagebox.askyesno("确认", "确定删除选中的快捷键吗？"):
            idx = self.tree.index(selected[0])
            self.hotkeys.pop(idx)
            self.save_hotkeys()
            self.refresh_list()
            self.register_global_hotkeys()
    
    def execute_hotkey(self, event):
        """执行快捷键动作"""
        selected = self.tree.selection()
        if not selected:
            return
        
        idx = self.tree.index(selected[0])
        hk = self.hotkeys[idx]
        
        action = hk.get('action', '')
        if action:
            try:
                if action.startswith('http'):
                    import webbrowser
                    webbrowser.open(action)
                elif action.startswith('cmd:'):
                    subprocess.Popen(action[4:])
                elif action.startswith('copy:'):
                    pyperclip.copy(action[5:])
                else:
                    subprocess.Popen(action, shell=True)
                    
                self.status_var.set(f"执行: {hk.get('description', '')}")
            except Exception as e:
                messagebox.showerror("错误", f"执行失败: {e}")
    
    def register_global_hotkeys(self):
        """注册全局快捷键"""
        # 先清除所有已注册的
        keyboard.unhook_all()
        
        # 重新注册系统级快捷键
        self.setup_hotkeys()
        
        # 为每个快捷键注册（如果需要）
        for i, hk in enumerate(self.hotkeys):
            try:
                # 这里可以添加特定快捷键的全局注册
                pass
            except:
                pass
    
    def toggle_window(self):
        """显示/隐藏窗口"""
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
        else:
            self.root.withdraw()
    
    def github_menu(self):
        """GitHub 菜单"""
        GitHubDialog(self.root, self.github_token)
    
    def load_github_token(self):
        """加载 GitHub Token"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('github_token', '')
            except:
                pass
        return ''
    
    def save_github_token(self, token):
        """保存 GitHub Token"""
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'github_token': token}, f)
        self.github_token = token
    
    def settings(self):
        """设置"""
        SettingsDialog(self.root, self)


class AddHotkeyDialog(tk.Toplevel):
    def __init__(self, parent, current_window):
        super().__init__(parent)
        self.title("添加快捷键")
        self.geometry("500x400")
        self.result = None
        
        ttk.Label(self, text="窗口:").pack(anchor=tk.W, padx=10, pady=5)
        self.window_var = tk.StringVar(value=current_window)
        ttk.Entry(self, textvariable=self.window_var, width=50).pack(fill=tk.X, padx=10)
        ttk.Label(self, text="(留空表示所有窗口)", foreground="gray").pack(anchor=tk.W, padx=10)
        
        ttk.Label(self, text="快捷键:").pack(anchor=tk.W, padx=10, pady=5)
        self.hotkey_var = tk.StringVar()
        hotkey_entry = ttk.Entry(self, textvariable=self.hotkey_var, width=30)
        hotkey_entry.pack(anchor=tk.W, padx=10)
        ttk.Label(self, text="示例: ctrl+shift+a, alt+f4, f1", foreground="gray").pack(anchor=tk.W, padx=10)
        
        ttk.Label(self, text="说明:").pack(anchor=tk.W, padx=10, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.desc_var, width=50).pack(fill=tk.X, padx=10)
        
        ttk.Label(self, text="执行动作:").pack(anchor=tk.W, padx=10, pady=5)
        self.action_var = tk.StringVar()
        action_combo = ttk.Combobox(self, textvariable=self.action_var, 
                                    values=["打开URL", "执行命令", "复制文本"],
                                    state="readonly")
        action_combo.pack(anchor=tk.W, padx=10)
        action_combo.bind("<<ComboboxSelected>>", self.show_action_entry)
        
        self.action_entry = ttk.Entry(self, width=50)
        
        ttk.Label(self, text="动作内容:").pack(anchor=tk.W, padx=10, pady=5)
        self.content_var = tk.StringVar()
        self.content_entry = ttk.Entry(self, textvariable=self.content_var, width=50)
        self.content_entry.pack(fill=tk.X, padx=10)
        
        ttk.Button(self, text="保存", command=self.save).pack(side=tk.BOTTOM, pady=10, padx=10)
        ttk.Button(self, text="取消", command=self.destroy).pack(side=tk.BOTTOM, pady=10)
    
    def show_action_entry(self, event):
        pass
    
    def save(self):
        window = self.window_var.get().strip()
        hotkey = self.hotkey_var.get().strip().lower()
        description = self.desc_var.get().strip()
        action_type = self.action_var.get()
        content = self.content_var.get().strip()
        
        if not hotkey or not description:
            messagebox.showwarning("提示", "快捷键和说明不能为空")
            return
        
        if action_type == "打开URL":
            if not content.startswith('http'):
                content = 'https://' + content
            action = content
        elif action_type == "执行命令":
            action = f"cmd:{content}"
        elif action_type == "复制文本":
            action = f"copy:{content}"
        else:
            action = content
        
        self.result = {
            'window': window,
            'hotkey': hotkey,
            'description': description,
            'action': action,
            'created': datetime.now().isoformat()
        }
        self.destroy()


class EditHotkeyDialog(AddHotkeyDialog):
    def __init__(self, parent, hotkey):
        super().__init__(parent, hotkey.get('window', ''))
        self.title("编辑快捷键")
        
        # 填充现有数据
        self.hotkey_var.set(hotkey.get('hotkey', ''))
        self.desc_var.set(hotkey.get('description', ''))
        action = hotkey.get('action', '')
        
        if action.startswith('http'):
            self.action_var.set("打开URL")
            self.content_var.set(action)
        elif action.startswith('cmd:'):
            self.action_var.set("执行命令")
            self.content_var.set(action[4:])
        elif action.startswith('copy:'):
            self.action_var.set("复制文本")
            self.content_var.set(action[5:])
        else:
            self.content_var.set(action)


class GitHubDialog(tk.Toplevel):
    def __init__(self, parent, token):
        super().__init__(parent)
        self.title("GitHub 集成")
        self.geometry("500x400")
        
        ttk.Label(self, text="GitHub Token:").pack(anchor=tk.W, padx=10, pady=5)
        self.token_var = tk.StringVar(value=token)
        ttk.Entry(self, textvariable=self.token_var, width=50, show="*").pack(fill=tk.X, padx=10)
        ttk.Label(self, text="Token 可在 GitHub Settings > Developer settings > Personal access tokens 创建",
                 wraplength=450, foreground="gray").pack(padx=10)
        
        ttk.Button(self, text="保存 Token", command=self.save_token).pack(pady=10)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        ttk.Button(self, text="📦 创建仓库并提交", command=self.create_repo_and_commit).pack(pady=10)
        ttk.Button(self, text="📤 提交当前更改", command=self.commit_changes).pack(pady=5)
        ttk.Button(self, text="📋 打开 GitHub", command=self.open_github).pack(pady=5)
        
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="blue").pack(pady=10)
    
    def save_token(self):
        token = self.token_var.get().strip()
        if token:
            # 获取当前窗口的父窗口的父窗口（HotkeyManager 实例）
            parent = self.master.master if hasattr(self.master, 'master') else self.master
            while hasattr(parent, 'master'):
                if isinstance(parent, HotkeyManager):
                    parent.save_github_token(token)
                    break
                parent = parent.master
            messagebox.showinfo("成功", "Token 已保存")
        else:
            messagebox.showwarning("提示", "请输入 Token")
    
    def create_repo_and_commit(self):
        """创建仓库并提交"""
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("提示", "请先设置 GitHub Token")
            return
        
        repo_name = simpledialog.askstring("创建仓库", "输入仓库名称:", parent=self)
        if not repo_name:
            return
        
        self.status_var.set("正在创建仓库...")
        self.update()
        
        try:
            # 创建仓库
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 检查用户
            resp = requests.get("https://api.github.com/user", headers=headers)
            if resp.status_code != 200:
                messagebox.showerror("错误", "Token 无效")
                return
            
            username = resp.json().get('login')
            
            # 创建仓库
            data = {"name": repo_name, "auto_init": True}
            resp = requests.post("https://api.github.com/user/repos", 
                               headers=headers, json=data)
            
            if resp.status_code == 201:
                self.status_var.set("仓库创建成功，正在提交...")
                
                # 获取当前目录的 Git 仓库
                subprocess.run(["git", "remote", "add", "origin", 
                              f"https://github.com/{username}/{repo_name}.git"], 
                              capture_output=True)
                subprocess.run(["git", "add", "."], capture_output=True)
                subprocess.run(["git", "commit", "-m", f"Initial commit - {datetime.now().isoformat()}"], 
                              capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", "master"], 
                              capture_output=True)
                
                self.status_var.set(f"✅ 已创建并提交到 https://github.com/{username}/{repo_name}")
                messagebox.showinfo("成功", f"仓库已创建并提交:\nhttps://github.com/{username}/{repo_name}")
            else:
                messagebox.showerror("错误", resp.json().get('message', '创建失败'))
                
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def commit_changes(self):
        """提交更改"""
        message = simpledialog.askstring("提交", "输入提交信息:", parent=self)
        if message:
            subprocess.run(["git", "add", "."], capture_output=True)
            result = subprocess.run(["git", "commit", "-m", message], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.status_var.set("已提交到本地仓库")
                subprocess.run(["git", "push"], capture_output=True)
                self.status_var.set("已推送到远程仓库")
                messagebox.showinfo("成功", "已提交并推送")
            else:
                messagebox.showwarning("提示", result.stderr or "没有更改需要提交")
    
    def open_github(self):
        """打开 GitHub"""
        import webbrowser
        webbrowser.open("https://github.com")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self.title("设置")
        self.geometry("400x300")
        self.manager = manager
        
        ttk.Label(self, text="全局快捷键:").pack(anchor=tk.W, padx=10, pady=10)
        ttk.Label(self, text="显示/隐藏主窗口: Ctrl+Alt+H", foreground="blue").pack(anchor=tk.W, padx=20)
        ttk.Label(self, text="保存快捷键: Ctrl+Alt+S", foreground="blue").pack(anchor=tk.W, padx=20)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        ttk.Button(self, text="📁 打开配置目录", command=self.open_config_dir).pack(pady=10)
        ttk.Button(self, text="💾 导出快捷键", command=self.export_hotkeys).pack(pady=5)
        ttk.Button(self, text="📥 导入快捷键", command=self.import_hotkeys).pack(pady=5)
        
        ttk.Label(self, text="数据文件:", foreground="gray").pack(pady=5)
        ttk.Label(self, text=HOTKEY_FILE, foreground="gray").pack(padx=10)
    
    def open_config_dir(self):
        """打开配置目录"""
        subprocess.Popen(["xdg-open", os.path.dirname(HOTKEY_FILE)])
    
    def export_hotkeys(self):
        """导出快捷键"""
        filepath = tk.filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="hotkeys_backup.json"
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.manager.hotkeys, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"已导出到 {filepath}")
    
    def import_hotkeys(self):
        """导入快捷键"""
        filepath = tk.filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if messagebox.askyesno("确认", f"导入 {len(data)} 个快捷键？"):
                self.manager.hotkeys = data
                self.manager.save_hotkeys()
                self.manager.refresh_list()
                messagebox.showinfo("成功", "已导入")


def main():
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    app = HotkeyManager(root)
    
    # 窗口关闭时清理
    def on_closing():
        app.running = False
        app.save_hotkeys()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
