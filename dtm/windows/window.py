import sys
if sys.version_info.major == 2:
    import Tkinter as tk
    import tkFileDialog
    import tkColorChooser
    import tkFont
elif  sys.version_info.major == 3:
    import tkinter as tk
    import tkinter.filedialog as tkFileDialog
    import tkinter.colorchooser as tkColorChooser
    import tkinter.font as tkFont
else:
    raise UserWarning("unknown python version?!")

import re
import os
from collections import OrderedDict

import dtm.windows.tk_font_chooser as tkFontChooser
import dtm.windows.editor as Editor
import dtm.windows.tag_config as TagConfig
import dtm.filters.filters as Filters
import dtm.filters.wordcolor as WordColor
import dtm.core.game_log_reader as GamelogReader
import dtm.core.config as Config
import dtm.core.util as util

# import psutil,time

def dict_to_font(dict_):
    return tkFont.Font(family=dict_["family"], size=dict_["size"], weight=dict_["weight"], slant=dict_["slant"], overstrike=dict_["overstrike"], underline=dict_["underline"])

class announcement_window(tk.Frame):
    def __init__(self, parent, id_):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.id = id_
        self.show_tags = False
        self.index_dict = {}
        Filters.expressions.add_window(self.id)
        self.customFont = dict_to_font(self.parent.gui_data['font_w%s' % self.id])
        self.config_gui = None
        self.vsb_pos = 1.0
        self.init_text_window()
        self.init_pulldown()

    def init_text_window(self):
        self.text = tk.Text(self, bg="black", wrap="word", font=self.customFont)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.text.config(cursor="")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind(util.mouse_buttons.right, self.popup)

        # link methods
        self.insert = self.text.insert
        self.delete = self.text.delete
        self.get = self.text.get
        self.index = self.text.index
        self.search = self.text.search
        self.tag_add = self.text.tag_add
        self.tag_config = self.text.tag_config
        self.tag_delete = self.text.tag_delete
        self.tag_names = self.text.tag_names
        self.tag_cget = self.text.tag_cget
        self.config = self.text.config
        self.yview = self.text.yview

    def init_pulldown(self):
        self.pulldown = tk.Menu(self, tearoff=0)
        bg = "white"
        if util.platform.win or util.platform.osx:
            bg = "SystemMenu"
        self.pulldown.add_command(label="Window %d" % self.id, activebackground=bg, activeforeground="black")
        self.pulldown.add("separator")
        self.pulldown.add_command(label="Change Font", command=self.edit_font)
        self.pulldown.add_command(label="Toggle Tags", command=self.toggle_tags)
        self.pulldown.add_command(label="Clear Window", command=self.clear_window)

    def popup(self, event):
        if self.focus_get() is not None:
            self.pulldown.tk_popup(event.x_root, event.y_root)

    def toggle_tags(self):
        self.show_tags = not self.show_tags
        self.config(state="normal")
        self.gen_tags()
        self.config(state="disabled")

    def edit_font(self):
        tup = tkFontChooser.askChooseFont(self.parent, defaultfont=self.customFont)
        if tup is not None:
            self.customFont = tkFont.Font(font=tup)
            self.parent.gui_data['font_w%s' % self.id] = self.customFont.actual()
            self.config(font=self.customFont)

    def close_config_gui(self):
        self.config_gui.destroy()
        self.config_gui = None
        Filters.expressions.save_filter_data()
        Filters.expressions.reload()
        self.parent.gen_tags()

    def clear_window(self):
        self.config(state="normal")
        self.delete('1.0', "end")
        self.gen_tags(clear_index_dict=True)
        self.config(state="disabled")

    def gen_tags(self, clear_index_dict=False):
        """Generate the tkinter tags for coloring
        """
        self.vsb_pos = (self.vsb.get()[1])
        colordict=Config.settings.word_color_dict
        for group_ in Filters.expressions.groups.items():
            # Group Coloring
            group = group_[1]
            for category_ in group.categories.items():
                category = category_[1]
                tag_name = "%s.%s" % (group.group, category.category)
                # set_elide =
                self.tag_config('%s.elide' % tag_name, foreground="#FFF", elide=not (self.show_tags and category.get_show(self.id)))
                self.tag_config(tag_name, foreground=group.color, elide=not category.get_show(self.id))
                if clear_index_dict:
                    self.index_dict[tag_name] = 0
                elif not (tag_name in self.index_dict):
                    self.index_dict[tag_name] = 0
        for color in colordict:
            # Word Coloring
            self.tag_config(color, foreground=colordict[color][0], background=colordict[color][1])
        if self.vsb_pos == 1.0:
            self.yview("end")

    def insert_ann(self, ann):
        def insert():
            anngroup=ann.get_group()
            anncat=ann.get_category()
            tag_name = "%s.%s" % (anngroup, anncat)
            self.insert("end", "[%s][%s] " % (anngroup, anncat), '%s.elide' % tag_name)
            regex=r"(\b"+'\\b|\\b'.join(WordColor.wd.get_all_group_words(anngroup))+"\\b)"
            tokenized = re.split(regex, ann.get_text())
            for token in tokenized:
                hlwordcolor=WordColor.wd.get_colorname(token,anngroup)
                self.insert("end", "%s" % token, tag_name)
                if hlwordcolor:
                    start="end-"+str(1+len(token))+"c"
                    end="end-1c"
                    self.tag_add(hlwordcolor,start,end)
            self.trim_announcements(tag_name)

        if ann.get_show(self.id):
            insert()
        elif Config.settings.save_hidden_announcements:
            insert()

    def trim_announcements(self, tag_name):
        if Config.settings.trim_announcements[self.id]:
            self.index_dict[tag_name] += 1
            if self.index_dict[tag_name] > Config.settings.trim_announcements[self.id]:
                index = int(float(self.text.index('%s.first' % tag_name)))
                self.delete("%d.0" % index, "%d.0" % (index + 1))

class TagPanel(tk.Frame):
    def __init__(self, parent, id, test="Tags"):
        tk.Frame.__init__(self, parent)

        self.parent = parent
        self.id_=id

        self.is_expanded = False

        self.grid(row=0, column=0, columnspan=4)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        self.toggle_button = tk.Button(self, text="<", width=1, command=self.toggle_expand, padx=1)
        self.toggle_button.grid(column=0, row=0, sticky="wns")

        self.subframe = tk.Frame(self, relief="sunken", borderwidth=1)
        self.subframe.grid(row=0, column=1, sticky="nsew")
        self.subframe.grid_forget()

        Filters.expressions.reload() # reload expressions to get the colors

        for i, group_ in enumerate(Filters.expressions.groups.items()):
            group_name = group_[0]
            group = group_[1]
            group_frame = tk.Frame(self.subframe)
            group_frame.grid(row=i,column=0)

            # Inside group_frame vv
            group_label = tk.Label(group_frame, text=group_name, anchor="w")
            group_color_button = tk.Button(group_frame, text="", command=lambda : self.color_picker(group_color_button, group), relief="sunken", activebackground=group.color, background=group.color, height=0, width=0, padx=2, pady=2, cursor="pencil")
            group_tggl_cb = tk.Checkbutton(group_frame)
            categories_frame = tk.Frame(group_frame)
            group_label.grid(row=0, column=0, columnspan=2, sticky="ew")
            group_color_button.grid(row=0, column=2, sticky="e")
            group_tggl_cb.grid(row=0, column=3)
            categories_frame.grid(row=1, column=0)
            #inside categories_frame vv
            for j, category_ in enumerate(group.categories.items()):
                category_name = category_[0]
                category = category_[1]
                category_shown = category.get_show(self.id_)
                category_label = tk.Label(categories_frame, text=category_name, anchor="e", relief="sunken")
                category_tggl_cb = tk.Checkbutton(categories_frame)
                if category_shown:
                    category_tggl_cb.select()
                category_tggl_cb.config(command=lambda : self.category_toggle(category, category_shown))
                category_label.grid(row=j, column=0)
                category_tggl_cb.grid(row=j, column=1)

    def category_toggle(self, category, shown):
        category.set_show(self.id_, not shown)

    def group_toggle(self, group):
        for show_ in group.category.show.items():
            print(TODO)


    def color_picker(self, button, group):
        new_color = tkColorChooser.askcolor()[1]
        if new_color is not None:
            button.config(background=new_color)
            group.set_color(new_color)

    def toggle_expand(self):
        if not self.is_expanded:
            self.expand()
        else:
            self.collapse()
        self.is_expanded = not self.is_expanded

    def expand(self):
        curr_width = self.parent.subpanels[self.id_].winfo_width()
        self.subframe.grid(row=0, column=1, columnspan=3)
        self.toggle_button.config(text= ">")
        self.parent.subpanels[self.id_].sash_place(0,int(2/3 * curr_width),1)

    def collapse(self):
        curr_width = self.parent.subpanels[self.id_].winfo_width()
        self.subframe.grid_forget()
        self.toggle_button.config(text= "<")
        self.parent.subpanels[self.id_].sash_place(0,int(curr_width) - 20,1)

class main_gui(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.iconbitmap(Config.settings.icon_path)
        self.title("Dwarf Thought Monitor")
        self.protocol('WM_DELETE_WINDOW', self.clean_exit)
        self.pack_propagate(False)
        self.config(bg="Gray", height=700, width=640)
        self.customFont = tkFont.Font(family='Lao UI', size=10)
        self.gui_data = Config.settings.load_gui_data()
        self.gamelog = GamelogReader.gamelog()
        self.connect()
        self.announcement_windows = OrderedDict([])
        self.tag_panels = OrderedDict([])
        self.subpanels = OrderedDict([])
        self.cpu_max = {}
        self.py = None
        if self.gui_data is None:
            self.gui_data = {"sash_place":int(700 / 3.236), "font_w0":self.customFont.actual(), "font_w1":self.customFont.actual()}
        self.locked = False
        self.init_menu()
        self.init_windows()
        self.gen_tags()
        # self.parallel()
        self.get_announcements(old=Config.settings.load_previous_announcements)
        self.pack_announcements()

    def init_menu(self):
        self.menu = tk.Menu(self, tearoff=0)

        options_menu = tk.Menu(self.menu, tearoff=0)
        options_menu.add_command(label="Filter Configuration", command=self.config_gui)
        options_menu.add_command(label="Edit filters.txt", command=self.open_filters)
        options_menu.add_command(label="Reload wordcolor.txt", command=WordColor.wd.reload)
        options_menu.add_command(label="Reload filters.txt", command=Filters.expressions.reload)
        options_menu.add_command(label="Reload Settings", command=self.reload_settings)

        self.settings_menu = tk.Menu(self.menu, tearoff=0)
        self.settings_menu.add_command(label="Set Directory", command=self.askpath)
        self.settings_menu.add_command(label="Lock Window", command=self.lock_window)
        self.menu.add_cascade(label="Settings", menu=self.settings_menu)
        self.menu.add_separator()
        self.menu.add_cascade(label="Options", menu=options_menu)
        # self.menu.add_command(label="Dump CPU info",command = self.dump_info)

        self.config(menu=self.menu)

    def connect(self):
        if not self.gamelog.connect():
            # TODO: add dialog when gamelog is not found
            pass

    # def dump_info(self):
    #     print('CPU-MAX:%f' % max(self.cpu_max["CPU"]))
    #     print('CPU-AVG:%f' % (sum(self.cpu_max["CPU"]) / len(self.cpu_max["CPU"])))

    #     print('MEM-MAX:%f MB' % max(self.cpu_max["MEM"]))
    #     print('MEM-AVG:%f MB' % (sum(self.cpu_max["MEM"]) / len(self.cpu_max["MEM"])))
    #     self.cpu_max["CPU"] = []
    #     self.cpu_max["MEM"] = []

    def init_windows(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.panel = tk.PanedWindow(self, orient="vertical", sashwidth=5)
        self.panel.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)

        for i in range(0, 2):
            curr_subpanel = tk.PanedWindow(self.panel, orient="horizontal", sashcursor="arrow")
            ann_win = announcement_window(self, i)
            tag_win = TagPanel(self, i)

            self.announcement_windows[i] = ann_win
            self.tag_panels[i] = tag_win
            self.subpanels[i] = curr_subpanel

            curr_subpanel.add(ann_win, stretch="always")
            curr_subpanel.add(tag_win)
            self.panel.add(curr_subpanel)

        self.panel.update_idletasks()
        # place sashed
        self.panel.sash_place(0, 0, self.gui_data["sash_place"])  # TODO: update to support multiple sashes
        curr_width = self.panel.winfo_width()
        self.subpanels[0].sash_place(0,int(curr_width) - 20,1)
        self.subpanels[1].sash_place(0,int(curr_width) - 20,1)

    def gen_tags(self):
        Filters.expressions.reload()
        for announcement_win in self.announcement_windows.items():
            announcement_win[1].config(state="normal")
            announcement_win[1].gen_tags()
            announcement_win[1].config(state="disabled")

    def clean_exit(self):
        self.gui_data["sash_place"] = self.panel.sash_coord(0)[1]
        Config.settings.save_gui_data(self.gui_data)
        self.destroy()

    def reload_settings(self):
        Config.settings.load()
        self.gen_tags()

    def edit_filters(self):
        Editor.TextEditor(Config.settings.filters_path)

    def open_filters(self):
        Editor.native_open(Config.settings.filters_path)

    def config_gui(self):
        Filters.expressions.reload()
        TagConfig.MainDialog(self)
        self.gen_tags()

    def askpath(self):
        path = Config.settings.get_gamelog_path()
        if os.path.isfile(path):
            new_path = tkFileDialog.askopenfilename(initialfile=path, parent=self, filetypes=[('text files', '.txt')], title="Locate DwarfFortress/gamelog.txt")
        else:
            new_path = tkFileDialog.askopenfilename(initialdir=path, parent=self, filetypes=[('text files', '.txt')], title="Locate DwarfFortress/gamelog.txt")
        if os.path.isfile(new_path):
            Config.settings.set_gamelog_path(new_path)
            Config.settings.save()
            self.connect()

    def lock_window(self):
        self.locked = not self.locked
        if util.platform.win:
            # Window decorations are not restored correctly on OS X when unlocking
            self.overrideredirect(self.locked)
        self.wm_attributes("-topmost", self.locked)
        tog_ = 'Unlock Window' if self.locked else 'Lock Window'
        self.settings_menu.entryconfig(self.settings_menu.index('end'), label=tog_)

    def get_announcements(self, old=False):
        if old:
            new_announcements = self.gamelog.get_old_announcements()
        else:
            new_announcements = self.gamelog.new()
        if new_announcements:
            for announcement_win in self.announcement_windows.items():
                announcement_win[1].vsb_pos = (announcement_win[1].vsb.get()[1])  # Jumps to end of list if the users scrollbar is @ end of list, otherwise holds current position
                announcement_win[1].text.config(state="normal")
            for ann in new_announcements:
                for announcement_win in self.announcement_windows.items():
                    announcement_win[1].insert_ann(ann)
            for announcement_win in self.announcement_windows.items():
                if announcement_win[1].vsb_pos == 1.0:
                    announcement_win[1].yview("end")
                announcement_win[1].text.config(state="disabled")
        self.after(1000, self.get_announcements)

    def pack_announcements(self):
        for announcement_win in self.announcement_windows.items():
            announcement_win[1].text.pack(side="top", fill="both", expand=True)
            # Why doesn't this always move to the end when you launch with setting: load_previous_announcements = True  ??
            announcement_win[1].yview("end")

if __name__ == "__main__":
    app = main_gui()
    app.mainloop()
