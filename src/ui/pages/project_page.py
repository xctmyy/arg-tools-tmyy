"""项目 / 线索管理页。

界面分三块：

    工具栏    新建 / 打开 / 保存工程 + 最近工程
    左侧      线索库（带搜索）
    右侧      线索编辑器（标题 / 来源 / 标签 / 内容）

线索的增删改会立即落盘，避免忘存导致丢数据。
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.config.settings import save_settings
from src.core import store
from src.ui.pages.base import BasePage
from src.ui.widgets import Card, StatusLine

NO_RECENT = "最近工程"


class ProjectPage(BasePage):
    title = "项目"
    description = "工程管理、线索库与整体进度"

    def __init__(self) -> None:
        self.project: store.Project | None = None
        self._editing_id: str | None = None
        self._list_widgets: list[ctk.CTkBaseClass] = []

    # ------------------------------------------------------------------ 构建
    def render(self, body: ctk.CTkFrame) -> None:
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self._build_toolbar(body)

        main = ctk.CTkFrame(body, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        self._build_list(main)
        self._build_editor(main)

        self._status = StatusLine(body)
        self._status.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self._set_enabled(False)
        self._refresh_recent()
        self._set_status("还没有打开工程，点左上角「新建工程」或「打开工程」开始")

    def _build_toolbar(self, body: ctk.CTkFrame) -> None:
        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        for text, cmd, width in (
            ("新建工程", self._new_project, 90),
            ("打开工程", self._open_project, 90),
            ("保存", self._save_project, 64),
        ):
            ctk.CTkButton(bar, text=text, width=width, height=30,
                          corner_radius=6, command=cmd).pack(side="left", padx=(0, 6))

        self._recent_menu = ctk.CTkOptionMenu(
            bar, values=[NO_RECENT], width=240, command=self._open_recent
        )
        self._recent_menu.pack(side="right")

        self._project_label = ctk.CTkLabel(
            bar, text="未打开工程", anchor="w", font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray62"),
        )
        self._project_label.pack(side="left", padx=(10, 0))

    def _build_list(self, parent: ctk.CTkFrame) -> None:
        card = Card(parent, title="线索库")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        b = card.body
        b.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(b, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.grid_columnconfigure(0, weight=1)

        self._search = ctk.CTkEntry(head, placeholder_text="搜索标题 / 内容 / 标签")
        self._search.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._search.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self._count_label = ctk.CTkLabel(
            head, text="", font=ctk.CTkFont(size=11), text_color=("gray45", "gray62")
        )
        self._count_label.grid(row=0, column=1)

        self._list = ctk.CTkScrollableFrame(b, width=240)
        self._list.grid(row=1, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(b, text="＋ 新建线索", height=30, corner_radius=6,
                      command=self._new_clue).grid(row=2, column=0,
                                                   sticky="ew", pady=(8, 0))

    def _build_editor(self, parent: ctk.CTkFrame) -> None:
        card = Card(parent, title="线索详情")
        card.grid(row=0, column=1, sticky="nsew")
        b = card.body
        b.grid_rowconfigure(4, weight=1)

        form = ctk.CTkFrame(b, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        self._f_title = self._form_row(form, 0, "标题")
        self._f_source = self._form_row(form, 1, "来源")
        self._f_tags = self._form_row(form, 2, "标签", "用逗号或空格分隔")

        ctk.CTkLabel(b, text="内容", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=3, column=0,
                                                     sticky="w", pady=(10, 2))
        self._f_content = ctk.CTkTextbox(b, wrap="word")
        self._f_content.grid(row=4, column=0, sticky="nsew")

        actions = ctk.CTkFrame(b, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        self._btn_save = ctk.CTkButton(actions, text="保存线索", height=30,
                                       corner_radius=6, command=self._save_clue)
        self._btn_save.pack(side="left", padx=(0, 6))
        self._btn_delete = ctk.CTkButton(
            actions, text="删除", width=64, height=30, corner_radius=6,
            fg_color=("#c0392b", "#8b2c22"), hover_color=("#a93226", "#6f231b"),
            command=self._delete_clue,
        )
        self._btn_delete.pack(side="left")

    def _form_row(self, parent: ctk.CTkFrame, row: int, label: str,
                  hint: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, width=48, anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=row, column=0,
                                                     sticky="w", pady=3)
        entry = ctk.CTkEntry(parent, placeholder_text=hint)
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        return entry

    # ------------------------------------------------------------------ 状态
    def _set_status(self, text: str, error: bool = False) -> None:
        self._status.error(text) if error else self._status.info(text)

    def _set_enabled(self, on: bool) -> None:
        state = "normal" if on else "disabled"
        for widget in (self._f_title, self._f_source, self._f_tags, self._f_content,
                       self._btn_save, self._btn_delete, self._search):
            widget.configure(state=state)

    def _sync_toolbar(self) -> None:
        if self.project is None:
            self._project_label.configure(text="未打开工程")
            return
        self._project_label.configure(
            text=f"{self.project.name}  ·  {self.project.root}  ·  "
                 f"{len(self.project.clues)} 条线索"
        )

    # ------------------------------------------------------------------ 工程
    def _new_project(self) -> None:
        folder = filedialog.askdirectory(title="选择一个空文件夹作为工程目录")
        if not folder:
            return
        root = Path(folder)
        try:
            self.project = store.Project.create(root.name, root)
        except store.ProjectError as e:
            messagebox.showerror("无法新建工程", str(e))
            return
        self._after_open(f"已新建工程「{self.project.name}」")

    def _open_project(self) -> None:
        folder = filedialog.askdirectory(title="选择工程目录")
        if folder:
            self._open_path(Path(folder))

    def _open_recent(self, path: str) -> None:
        if path != NO_RECENT:
            self._open_path(Path(path))

    def _open_path(self, root: Path) -> None:
        if not store.Project.is_project(root):
            messagebox.showerror("打不开", f"这个目录不是 ARG 工程：\n{root}")
            self._refresh_recent()
            return
        try:
            self.project = store.Project.open(root)
        except store.ProjectError as e:
            messagebox.showerror("打不开", str(e))
            return
        self._after_open(f"已打开工程「{self.project.name}」")

    def _settings(self):
        """取应用级设置；页面独立使用时可能为 None。"""
        return getattr(self.window, "settings", None)

    def _refresh_recent(self) -> None:
        settings = self._settings()
        paths = list(settings.recent_projects) if settings else []
        self._recent_menu.configure(values=paths or [NO_RECENT])
        self._recent_menu.set(paths[0] if paths else NO_RECENT)

    def _after_open(self, message: str) -> None:
        self._editing_id = None
        self._clear_form()
        self._set_enabled(True)
        self._sync_toolbar()
        self._refresh_list()

        settings = self._settings()
        if settings is not None and self.project is not None and self.project.root:
            settings.touch_recent(self.project.root)
            save_settings(settings)
        self._refresh_recent()
        self._set_status(message)

    def _save_project(self) -> None:
        if self.project is None:
            return
        try:
            self.project.save()
        except store.ProjectError as e:
            self._set_status(str(e), error=True)
            return
        self._sync_toolbar()
        self._set_status("工程已保存")

    # ------------------------------------------------------------------ 线索
    def _refresh_list(self) -> None:
        for widget in self._list_widgets:
            widget.destroy()
        self._list_widgets.clear()
        if self.project is None:
            return

        clues = self.project.find_clues(self._search.get().strip())
        self._count_label.configure(text=f"{len(clues)}/{len(self.project.clues)}")

        if not clues:
            label = ctk.CTkLabel(self._list, text="没有匹配的线索",
                                 font=ctk.CTkFont(size=11),
                                 text_color=("gray50", "gray60"))
            label.grid(row=0, column=0, pady=10)
            self._list_widgets.append(label)
            return

        for i, clue in enumerate(clues):
            title = clue.title or "（无标题）"
            if clue.tags:
                title += f"   #{' #'.join(clue.tags)}"
            btn = ctk.CTkButton(
                self._list, text=title, anchor="w", height=30, corner_radius=6,
                fg_color=("gray78", "gray24") if clue.id == self._editing_id
                else "transparent",
                text_color=("gray15", "gray90"),
                hover_color=("gray72", "gray30"),
                command=lambda c=clue: self._load_clue(c),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self._list_widgets.append(btn)

    def _load_clue(self, clue: store.Clue) -> None:
        self._editing_id = clue.id
        self._f_title.delete(0, "end")
        self._f_title.insert(0, clue.title)
        self._f_source.delete(0, "end")
        self._f_source.insert(0, clue.source)
        self._f_tags.delete(0, "end")
        self._f_tags.insert(0, " ".join(clue.tags))
        self._f_content.delete("1.0", "end")
        self._f_content.insert("1.0", clue.content)
        self._refresh_list()
        self._set_status(f"正在编辑「{clue.title or '无标题'}」")

    def _new_clue(self) -> None:
        self._editing_id = None
        self._clear_form()
        self._refresh_list()
        self._set_status("填写后点「保存线索」新增")

    def _save_clue(self) -> None:
        if self.project is None:
            return
        title = self._f_title.get().strip()
        content = self._f_content.get("1.0", "end-1c")
        if not title and not content:
            self._set_status("标题和内容不能都为空", error=True)
            return

        tags = [t for t in self._f_tags.get().replace(",", " ").replace("，", " ").split() if t]
        source = self._f_source.get().strip()

        if self._editing_id is None:
            clue = self.project.add_clue(title=title, content=content,
                                         source=source, tags=tags)
            self._editing_id = clue.id
            message = f"已新增线索「{title or '无标题'}」"
        else:
            if not self.project.update_clue(self._editing_id, title=title,
                                            content=content, source=source, tags=tags):
                self._set_status("线索已不存在，可能被删掉了", error=True)
                return
            message = f"已更新线索「{title or '无标题'}」"

        self.project.save()
        self._sync_toolbar()
        self._refresh_list()
        self._set_status(message)

    def _delete_clue(self) -> None:
        if self.project is None or self._editing_id is None:
            self._set_status("没有选中线索", error=True)
            return
        clue = self.project.get_clue(self._editing_id)
        if clue is None:
            return
        if not messagebox.askyesno("确认删除", f"确定删除「{clue.title or '无标题'}」？"):
            return
        self.project.remove_clue(clue.id)
        self.project.save()
        self._editing_id = None
        self._clear_form()
        self._sync_toolbar()
        self._refresh_list()
        self._set_status("线索已删除")

    def _clear_form(self) -> None:
        self._f_title.delete(0, "end")
        self._f_source.delete(0, "end")
        self._f_tags.delete(0, "end")
        self._f_content.delete("1.0", "end")
