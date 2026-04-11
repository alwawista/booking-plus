"""Графический интерфейс системы бронирования на tkinter."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

import backend
from models import Booking, Table, User

load_dotenv()

# Подписи под полями booking_time (см. _parse_datetime_user).
BOOKING_TIME_HINT = (
    "Формат: ГГГГ-ММ-ДД ЧЧ:ММ — без часового пояса трактуется как UTC; "
    "или полная ISO-8601 с поясом, напр. 2026-04-11T18:00:00+03:00 или с Z на конце."
)


def _parse_datetime_user(s: str) -> datetime:
    """Парсит дату/время для брони и проверки доступности (UTC если зона не указана)."""
    s = s.strip()
    if not s:
        raise ValueError("Укажите дату и время.")
    s = s.replace("Z", "+00:00")
    if "T" not in s and len(s) <= 16 and " " in s:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _fmt_dt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M %Z")
    return str(v)


def _optional_int(s: str) -> int | None:
    t = s.strip()
    if not t:
        return None
    return int(t)


class BookingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Бронирование столиков")
        self.geometry("960x640")
        self.minsize(800, 520)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_tab_db(nb)
        self._build_tab_users(nb)
        self._build_tab_tables(nb)
        self._build_tab_bookings(nb)
        self._build_tab_availability(nb)

    # --- общее ---

    def _show_exc(self, title: str, exc: BaseException) -> None:
        messagebox.showerror(title, str(exc))

    # --- База данных ---

    def _build_tab_db(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="База данных")

        ttk.Label(
            tab,
            text="Создание таблиц users, tables, bookings (DDL), если их ещё нет.",
            wraplength=700,
        ).pack(anchor=tk.W)

        def run_ddl() -> None:
            try:
                backend.create_tables()
                messagebox.showinfo("Готово", "Таблицы проверены/созданы.")
            except Exception as e:
                self._show_exc("Ошибка DDL", e)

        ttk.Button(tab, text="Создать таблицы", command=run_ddl).pack(anchor=tk.W, pady=(12, 0))

    # --- Пользователи ---

    def _build_tab_users(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Пользователи")

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "email", "full_name", "phone", "is_active")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        for c, w in zip(
            cols,
            (50, 200, 160, 120, 70),
        ):
            tree.heading(c, text=c)
            tree.column(c, width=w, stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh() -> None:
            try:
                rows = backend.get_all_users()
                tree.delete(*tree.get_children())
                for u in rows:
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            u.id,
                            u.email,
                            u.full_name,
                            u.phone or "",
                            u.is_active,
                        ),
                    )
            except Exception as e:
                self._show_exc("Список пользователей", e)

        ttk.Button(tab, text="Обновить список", command=refresh).pack(anchor=tk.W, pady=(0, 8))

        form = ttk.LabelFrame(tab, text="Создать пользователя", padding=8)
        form.pack(fill=tk.X, pady=(0, 8))

        ue = ttk.Entry(form, width=40)
        ph = ttk.Entry(form, width=40)
        fn = ttk.Entry(form, width=40)
        pho = ttk.Entry(form, width=40)
        ia = tk.BooleanVar(value=True)
        ttk.Label(form, text="email").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        ue.grid(row=0, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(form, text="password_hash").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ph.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(form, text="full_name").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        fn.grid(row=2, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(form, text="phone (необяз.)").grid(row=3, column=0, sticky=tk.W, padx=4, pady=2)
        pho.grid(row=3, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Checkbutton(form, text="is_active", variable=ia).grid(
            row=4, column=1, sticky=tk.W, padx=4, pady=2
        )
        form.columnconfigure(1, weight=1)

        def do_create() -> None:
            try:
                u = User(
                    email=ue.get().strip(),
                    password_hash=ph.get().strip(),
                    full_name=fn.get().strip(),
                    phone=pho.get().strip() or None,
                    is_active=ia.get(),
                )
                new_id = backend.create_user(u)
                messagebox.showinfo("Создано", f"id = {new_id}")
                refresh()
            except Exception as e:
                self._show_exc("Создание пользователя", e)

        ttk.Button(form, text="Создать", command=do_create).grid(
            row=5, column=1, sticky=tk.W, padx=4, pady=6
        )

        edit = ttk.LabelFrame(tab, text="Поиск / изменение / удаление по id", padding=8)
        edit.pack(fill=tk.X)

        eid = ttk.Entry(edit, width=12)
        ue2 = ttk.Entry(edit, width=40)
        ph2 = ttk.Entry(edit, width=40)
        fn2 = ttk.Entry(edit, width=40)
        pho2 = ttk.Entry(edit, width=40)
        ia2 = tk.BooleanVar(value=True)

        ttk.Label(edit, text="id").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        eid.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(edit, text="email").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ue2.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(edit, text="password_hash").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        ph2.grid(row=2, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(edit, text="full_name").grid(row=3, column=0, sticky=tk.W, padx=4, pady=2)
        fn2.grid(row=3, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(edit, text="phone").grid(row=4, column=0, sticky=tk.W, padx=4, pady=2)
        pho2.grid(row=4, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Checkbutton(edit, text="is_active", variable=ia2).grid(
            row=5, column=1, sticky=tk.W, padx=4, pady=2
        )
        edit.columnconfigure(1, weight=1)

        def load_one() -> None:
            try:
                uid = int(eid.get().strip())
                u = backend.get_user_by_id(uid)
                if u is None:
                    messagebox.showwarning("Не найдено", f"Пользователь id={uid} не найден.")
                    return
                ue2.delete(0, tk.END)
                ue2.insert(0, u.email)
                ph2.delete(0, tk.END)
                ph2.insert(0, u.password_hash)
                fn2.delete(0, tk.END)
                fn2.insert(0, u.full_name)
                pho2.delete(0, tk.END)
                pho2.insert(0, u.phone or "")
                ia2.set(u.is_active)
            except Exception as e:
                self._show_exc("Загрузка пользователя", e)

        def do_update() -> None:
            try:
                uid = int(eid.get().strip())
                u = User(
                    id=uid,
                    email=ue2.get().strip(),
                    password_hash=ph2.get().strip(),
                    full_name=fn2.get().strip(),
                    phone=pho2.get().strip() or None,
                    is_active=ia2.get(),
                )
                n = backend.update_user(u)
                messagebox.showinfo("Обновлено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Обновление пользователя", e)

        def do_delete() -> None:
            try:
                uid = int(eid.get().strip())
                if not messagebox.askyesno("Удаление", f"Удалить пользователя id={uid}?"):
                    return
                n = backend.delete_user(uid)
                messagebox.showinfo("Удалено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Удаление пользователя", e)

        bf = ttk.Frame(edit)
        bf.grid(row=6, column=1, sticky=tk.W, padx=4, pady=6)
        ttk.Button(bf, text="Загрузить", command=load_one).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Обновить", command=do_update).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Удалить", command=do_delete).pack(side=tk.LEFT)

        def on_tree_select(_evt: Any) -> None:
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            if vals:
                eid.delete(0, tk.END)
                eid.insert(0, str(vals[0]))
                load_one()

        tree.bind("<<TreeviewSelect>>", on_tree_select)

    # --- Столы ---

    def _build_tab_tables(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Столы")

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "name", "capacity", "location", "is_active")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (50, 140, 80, 160, 70)):
            tree.heading(c, text=c)
            tree.column(c, width=w, stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh() -> None:
            try:
                rows = backend.get_all_tables()
                tree.delete(*tree.get_children())
                for trow in rows:
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            trow.id,
                            trow.name,
                            trow.capacity,
                            trow.location or "",
                            trow.is_active,
                        ),
                    )
            except Exception as e:
                self._show_exc("Список столов", e)

        ttk.Button(tab, text="Обновить список", command=refresh).pack(anchor=tk.W, pady=(0, 8))

        form = ttk.LabelFrame(tab, text="Создать стол", padding=8)
        form.pack(fill=tk.X, pady=(0, 8))

        ne = ttk.Entry(form, width=30)
        cap = ttk.Entry(form, width=10)
        loc = ttk.Entry(form, width=40)
        ia = tk.BooleanVar(value=True)
        ttk.Label(form, text="name").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        ne.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(form, text="capacity").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        cap.grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(form, text="location (необяз.)").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        loc.grid(row=2, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Checkbutton(form, text="is_active", variable=ia).grid(
            row=3, column=1, sticky=tk.W, padx=4, pady=2
        )
        form.columnconfigure(1, weight=1)

        def do_create() -> None:
            try:
                trow = Table(
                    name=ne.get().strip(),
                    capacity=int(cap.get().strip()),
                    location=loc.get().strip() or None,
                    is_active=ia.get(),
                )
                new_id = backend.create_table(trow)
                messagebox.showinfo("Создано", f"id = {new_id}")
                refresh()
            except Exception as e:
                self._show_exc("Создание стола", e)

        ttk.Button(form, text="Создать", command=do_create).grid(
            row=4, column=1, sticky=tk.W, padx=4, pady=6
        )

        edit = ttk.LabelFrame(tab, text="Поиск / изменение / удаление по id", padding=8)
        edit.pack(fill=tk.X)

        eid = ttk.Entry(edit, width=12)
        ne2 = ttk.Entry(edit, width=30)
        cap2 = ttk.Entry(edit, width=10)
        loc2 = ttk.Entry(edit, width=40)
        ia2 = tk.BooleanVar(value=True)

        ttk.Label(edit, text="id").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        eid.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(edit, text="name").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ne2.grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(edit, text="capacity").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        cap2.grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(edit, text="location").grid(row=3, column=0, sticky=tk.W, padx=4, pady=2)
        loc2.grid(row=3, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Checkbutton(edit, text="is_active", variable=ia2).grid(
            row=4, column=1, sticky=tk.W, padx=4, pady=2
        )
        edit.columnconfigure(1, weight=1)

        def load_one() -> None:
            try:
                tid = int(eid.get().strip())
                trow = backend.get_table_by_id(tid)
                if trow is None:
                    messagebox.showwarning("Не найдено", f"Стол id={tid} не найден.")
                    return
                ne2.delete(0, tk.END)
                ne2.insert(0, trow.name)
                cap2.delete(0, tk.END)
                cap2.insert(0, str(trow.capacity))
                loc2.delete(0, tk.END)
                loc2.insert(0, trow.location or "")
                ia2.set(trow.is_active)
            except Exception as e:
                self._show_exc("Загрузка стола", e)

        def do_update() -> None:
            try:
                tid = int(eid.get().strip())
                trow = Table(
                    id=tid,
                    name=ne2.get().strip(),
                    capacity=int(cap2.get().strip()),
                    location=loc2.get().strip() or None,
                    is_active=ia2.get(),
                )
                n = backend.update_table(trow)
                messagebox.showinfo("Обновлено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Обновление стола", e)

        def do_delete() -> None:
            try:
                tid = int(eid.get().strip())
                if not messagebox.askyesno("Удаление", f"Удалить стол id={tid}?"):
                    return
                n = backend.delete_table(tid)
                messagebox.showinfo("Удалено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Удаление стола", e)

        bf = ttk.Frame(edit)
        bf.grid(row=5, column=1, sticky=tk.W, padx=4, pady=6)
        ttk.Button(bf, text="Загрузить", command=load_one).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Обновить", command=do_update).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Удалить", command=do_delete).pack(side=tk.LEFT)

        def on_tree_select(_evt: Any) -> None:
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            if vals:
                eid.delete(0, tk.END)
                eid.insert(0, str(vals[0]))
                load_one()

        tree.bind("<<TreeviewSelect>>", on_tree_select)

    # --- Бронирования ---

    def _build_tab_bookings(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Бронирования")

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "user_id", "table_id", "booking_time", "guests", "active", "request")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=9)
        widths = (40, 60, 60, 150, 50, 50, 200)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, stretch=c == "request")
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh() -> None:
            try:
                rows = backend.get_all_bookings()
                tree.delete(*tree.get_children())
                for b in rows:
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            b.id,
                            b.user_id,
                            b.table_id,
                            _fmt_dt(b.booking_time),
                            b.guests_count,
                            b.is_active,
                            (b.special_request or "")[:80],
                        ),
                    )
            except Exception as e:
                self._show_exc("Список бронирований", e)

        ttk.Button(tab, text="Обновить список", command=refresh).pack(anchor=tk.W, pady=(0, 6))

        form = ttk.LabelFrame(tab, text="Создать бронирование", padding=8)
        form.pack(fill=tk.X, pady=(6, 8))

        uid = ttk.Entry(form, width=12)
        tid = ttk.Entry(form, width=12)
        bt = ttk.Entry(form, width=36)
        gc = ttk.Entry(form, width=8)
        sr = ttk.Entry(form, width=50)
        ia = tk.BooleanVar(value=True)

        r = 0
        ttk.Label(form, text="user_id").grid(row=r, column=0, sticky=tk.W, padx=4, pady=2)
        uid.grid(row=r, column=1, sticky=tk.W, padx=4, pady=2)
        r += 1
        ttk.Label(form, text="table_id").grid(row=r, column=0, sticky=tk.W, padx=4, pady=2)
        tid.grid(row=r, column=1, sticky=tk.W, padx=4, pady=2)
        r += 1
        ttk.Label(form, text="booking_time").grid(row=r, column=0, sticky=tk.NW, padx=4, pady=2)
        bt.grid(row=r, column=1, sticky=tk.W, padx=4, pady=2)
        r += 1
        ttk.Label(
            form,
            text=BOOKING_TIME_HINT,
            wraplength=520,
            justify=tk.LEFT,
        ).grid(row=r, column=1, sticky=tk.W, padx=4, pady=(0, 6))
        r += 1
        ttk.Label(form, text="guests_count").grid(row=r, column=0, sticky=tk.W, padx=4, pady=2)
        gc.grid(row=r, column=1, sticky=tk.W, padx=4, pady=2)
        r += 1
        ttk.Label(form, text="special_request (необяз.)").grid(row=r, column=0, sticky=tk.W, padx=4, pady=2)
        sr.grid(row=r, column=1, sticky=tk.EW, padx=4, pady=2)
        r += 1
        ttk.Checkbutton(form, text="is_active", variable=ia).grid(
            row=r, column=1, sticky=tk.W, padx=4, pady=2
        )
        form.columnconfigure(1, weight=1)

        def do_create() -> None:
            try:
                b = Booking(
                    user_id=int(uid.get().strip()),
                    table_id=int(tid.get().strip()),
                    booking_time=_parse_datetime_user(bt.get()),
                    guests_count=int(gc.get().strip()),
                    special_request=sr.get().strip() or None,
                    is_active=ia.get(),
                )
                new_id = backend.create_booking(b)
                messagebox.showinfo("Создано", f"id = {new_id}")
                refresh()
            except Exception as e:
                self._show_exc("Создание бронирования", e)

        ttk.Button(form, text="Создать", command=do_create).grid(
            row=r + 1, column=1, sticky=tk.W, padx=4, pady=6
        )

        edit = ttk.LabelFrame(tab, text="Поиск / изменение / удаление по id", padding=8)
        edit.pack(fill=tk.X)

        eid = ttk.Entry(edit, width=12)
        uid2 = ttk.Entry(edit, width=12)
        tid2 = ttk.Entry(edit, width=12)
        bt2 = ttk.Entry(edit, width=36)
        gc2 = ttk.Entry(edit, width=8)
        sr2 = ttk.Entry(edit, width=50)
        ia2 = tk.BooleanVar(value=True)

        er = 0
        ttk.Label(edit, text="id").grid(row=er, column=0, sticky=tk.W, padx=4, pady=2)
        eid.grid(row=er, column=1, sticky=tk.W, padx=4, pady=2)
        er += 1
        ttk.Label(edit, text="user_id").grid(row=er, column=0, sticky=tk.W, padx=4, pady=2)
        uid2.grid(row=er, column=1, sticky=tk.W, padx=4, pady=2)
        er += 1
        ttk.Label(edit, text="table_id").grid(row=er, column=0, sticky=tk.W, padx=4, pady=2)
        tid2.grid(row=er, column=1, sticky=tk.W, padx=4, pady=2)
        er += 1
        ttk.Label(edit, text="booking_time").grid(row=er, column=0, sticky=tk.NW, padx=4, pady=2)
        bt2.grid(row=er, column=1, sticky=tk.W, padx=4, pady=2)
        er += 1
        ttk.Label(
            edit,
            text=BOOKING_TIME_HINT,
            wraplength=520,
            justify=tk.LEFT,
        ).grid(row=er, column=1, sticky=tk.W, padx=4, pady=(0, 6))
        er += 1
        ttk.Label(edit, text="guests_count").grid(row=er, column=0, sticky=tk.W, padx=4, pady=2)
        gc2.grid(row=er, column=1, sticky=tk.W, padx=4, pady=2)
        er += 1
        ttk.Label(edit, text="special_request").grid(row=er, column=0, sticky=tk.W, padx=4, pady=2)
        sr2.grid(row=er, column=1, sticky=tk.EW, padx=4, pady=2)
        er += 1
        ttk.Checkbutton(edit, text="is_active", variable=ia2).grid(
            row=er, column=1, sticky=tk.W, padx=4, pady=2
        )
        edit.columnconfigure(1, weight=1)

        def load_one() -> None:
            try:
                bid = int(eid.get().strip())
                b = backend.get_booking_by_id(bid)
                if b is None:
                    messagebox.showwarning("Не найдено", f"Бронирование id={bid} не найдено.")
                    return
                uid2.delete(0, tk.END)
                uid2.insert(0, str(b.user_id))
                tid2.delete(0, tk.END)
                tid2.insert(0, str(b.table_id))
                bt2.delete(0, tk.END)
                bt2.insert(0, b.booking_time.strftime("%Y-%m-%d %H:%M"))
                gc2.delete(0, tk.END)
                gc2.insert(0, str(b.guests_count))
                sr2.delete(0, tk.END)
                sr2.insert(0, b.special_request or "")
                ia2.set(b.is_active)
            except Exception as e:
                self._show_exc("Загрузка бронирования", e)

        def do_update() -> None:
            try:
                bid = int(eid.get().strip())
                b = Booking(
                    id=bid,
                    user_id=int(uid2.get().strip()),
                    table_id=int(tid2.get().strip()),
                    booking_time=_parse_datetime_user(bt2.get()),
                    guests_count=int(gc2.get().strip()),
                    special_request=sr2.get().strip() or None,
                    is_active=ia2.get(),
                )
                n = backend.update_booking(b)
                messagebox.showinfo("Обновлено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Обновление бронирования", e)

        def do_delete() -> None:
            try:
                bid = int(eid.get().strip())
                if not messagebox.askyesno("Удаление", f"Удалить бронирование id={bid}?"):
                    return
                n = backend.delete_booking(bid)
                messagebox.showinfo("Удалено", f"Затронуто строк: {n}")
                refresh()
            except Exception as e:
                self._show_exc("Удаление бронирования", e)

        bf = ttk.Frame(edit)
        bf.grid(row=er + 1, column=1, sticky=tk.W, padx=4, pady=6)
        ttk.Button(bf, text="Загрузить", command=load_one).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Обновить", command=do_update).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Удалить", command=do_delete).pack(side=tk.LEFT)

        def on_tree_select(_evt: Any) -> None:
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            if vals:
                eid.delete(0, tk.END)
                eid.insert(0, str(vals[0]))
                load_one()

        tree.bind("<<TreeviewSelect>>", on_tree_select)

    # --- Доступность ---

    def _build_tab_availability(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Доступность")

        ttk.Label(
            tab,
            text="Проверка: стол свободен в полуинтервале [время, время + длительность слота). "
            "Учитываются только активные брони. exclude_booking_id — при редактировании брони.",
            wraplength=880,
        ).pack(anchor=tk.W)

        frm = ttk.Frame(tab, padding=(0, 12, 0, 0))
        frm.pack(fill=tk.X)

        tid = ttk.Entry(frm, width=12)
        bt = ttk.Entry(frm, width=32)
        hours = ttk.Entry(frm, width=8)
        excl = ttk.Entry(frm, width=12)
        hours.insert(0, "2")

        r = 0
        ttk.Label(frm, text="table_id").grid(row=r, column=0, sticky=tk.W, padx=4, pady=4)
        tid.grid(row=r, column=1, sticky=tk.W, padx=4, pady=4)
        r += 1
        ttk.Label(frm, text="booking_time").grid(row=r, column=0, sticky=tk.NW, padx=4, pady=4)
        bt.grid(row=r, column=1, sticky=tk.W, padx=4, pady=4)
        r += 1
        ttk.Label(
            frm,
            text=BOOKING_TIME_HINT,
            wraplength=520,
            justify=tk.LEFT,
        ).grid(row=r, column=1, sticky=tk.W, padx=4, pady=(0, 4))
        r += 1
        ttk.Label(frm, text="длительность слота (часы)").grid(row=r, column=0, sticky=tk.W, padx=4, pady=4)
        hours.grid(row=r, column=1, sticky=tk.W, padx=4, pady=4)
        r += 1
        ttk.Label(frm, text="exclude_booking_id (необяз.)").grid(row=r, column=0, sticky=tk.W, padx=4, pady=4)
        excl.grid(row=r, column=1, sticky=tk.W, padx=4, pady=4)

        out = tk.Text(tab, height=4, width=80, state=tk.DISABLED, wrap=tk.WORD)

        def show_result(text: str) -> None:
            out.configure(state=tk.NORMAL)
            out.delete("1.0", tk.END)
            out.insert(tk.END, text)
            out.configure(state=tk.DISABLED)

        def check() -> None:
            try:
                table_id = int(tid.get().strip())
                booking_time = _parse_datetime_user(bt.get())
                h = float(hours.get().strip().replace(",", "."))
                slot = timedelta(hours=h)
                ex = _optional_int(excl.get())
                ok = backend.check_table_availability(
                    table_id,
                    booking_time,
                    slot_duration=slot,
                    exclude_booking_id=ex,
                )
                show_result(
                    "Результат: стол "
                    + ("свободен" if ok else "занят")
                    + f" (table_id={table_id}, slot={h} ч)."
                )
            except Exception as e:
                self._show_exc("Проверка доступности", e)

        ttk.Button(frm, text="Проверить", command=check).grid(
            row=r + 1, column=1, sticky=tk.W, padx=4, pady=12
        )

        ttk.Label(tab, text="Результат:").pack(anchor=tk.W, pady=(8, 0))
        out.pack(fill=tk.BOTH, expand=True, pady=(4, 0))


def main() -> None:
    app = BookingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
