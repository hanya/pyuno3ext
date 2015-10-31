
PYTHON_SH_BASE = """#!/bin/sh
#**************************************************************
#  
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#  
#    http://www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#  
#**************************************************************

sd_prog="%%OFFICE_PROGRAM%%"
ext_dir="%%EXTENSION_DIR%%"

# Set PATH so that crash_report is found:
PATH=$sd_prog${PATH+:$PATH}
export PATH

# Set LD_LIBRARY_PATH so that "import pyuno" finds libpyuno.so:
LD_LIBRARY_PATH=$ext_dir/lib:$sd_prog:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export LD_LIBRARY_PATH

# Set UNO_PATH so that "officehelper.bootstrap()" can find soffice executable:
: ${UNO_PATH=$sd_prog}
export UNO_PATH

# Set URE_BOOTSTRAP so that "uno.getComponentContext()" bootstraps a complete
# OOo UNO environment:
: ${URE_BOOTSTRAP=vnd.sun.star.pathname:$sd_prog/fundamentalrc}
export URE_BOOTSTRAP
PYTHONPATH=$ext_dir/lib/python%%PYVERSION%%:$ext_dir/lib/python%%PYVERSION%%/lib-dynload:$ext_dir/lib
export PYTHONPATH
PYTHONHOME=$ext_dir
export PYTHONHOME

# execute binary
exec "$ext_dir/bin/python3" "$@"
"""

import xml.dom.minidom
import unohelper
import os
import os.path
import stat
import platform

components_xml = """<?xml version="1.0"?>
<components xmlns="http://openoffice.org/2010/uno-components">
<component loader="com.sun.star.loader.SharedLibrary" uri="vnd.sun.star.expand:$OOO_BASE_DIR/program/pythonloader.uno.so">
<implementation name="org.openoffice.comp.pyuno.Loader">
<service name="com.sun.star.loader.Python"/>
</implementation>
</component>
<component loader="com.sun.star.loader.Python" uri="vnd.openoffice.pymodule:pythonscript">
<implementation name="org.openoffice.pyuno.LanguageScriptProviderForPython">
<service name="com.sun.star.script.provider.LanguageScriptProvider"/>
<service name="com.sun.star.script.provider.ScriptProviderForPython"/>
</implementation>
</component>
<component loader="com.sun.star.loader.Python" uri="vnd.openoffice.pymodule:mailmerge">
<implementation name="org.openoffice.pyuno.MailMessage">
<service name="com.sun.star.mail.MailMessage"/>
</implementation>
<implementation name="org.openoffice.pyuno.MailServiceProvider">
<service name="com.sun.star.mail.MailServiceProvider"/>
</implementation>
</component>
</components>"""


class BaseParser:
    
    def __init__(self, ctx):
        self.ctx = ctx
    
    def _create(self, name):
        return self.ctx.getServiceManager().createInstanceWithContext(name, self.ctx)
    
    def _substitute_path(self, path):
        return unohelper.fileUrlToSystemPath(
            self._create("com.sun.star.util.PathSubstitution").\
                substituteVariables("$(prog)/services.rdb", True))
    
    def _check_file(self):
        if not os.path.exists(self.path):
            return "File not exists: " + self.path
        # check file writable and try to make the file writable
        if not os.access(self.path, os.W_OK):
            st = os.stat(self.path)
            try:
                os.chmod(self.path, st.st_mode | stat.S_IWOTH)
            except:
                return "Unable to make the file writable: " + self.path
    
    def show_message(self, message, title):
        """ Show message in the message box
            @param message message to show on the box
            @param title title shown on the title bar
        """
        toolkit = self._create("com.sun.star.awt.Toolkit")
        msgbox = toolkit.createMessageBox(None, 0, 1, title, message)
        msgbox.execute()


class Parser(BaseParser):
    """ Add or remove original component registrations in services.rdb file.
        If you do not have right to write to the file, the operation fails.
    """
    
    URI_MAILMERGE = "vnd.openoffice.pymodule:mailmerge"
    URI_PYTHONLOADER = "vnd.sun.star.expand:$OOO_BASE_DIR/program/pythonloader.uno.so"
    URI_PYTHONSCRIPT = "vnd.openoffice.pymodule:pythonscript"
    
    def __init__(self, ctx, dest):
        BaseParser.__init__(self, ctx)
        self.path = self._substitute_path("$(prog)/services.rdb")
        self.dom = None
        self.dest = dest
    
    def _load(self):
        ret = None
        message = self._check_file()
        if message:
            return self.show_message(message, "Error")
        dom = self.dom = xml.dom.minidom.parse(self.path)
        components = dom.getElementsByTagName("components")
        if len(components) == 1:
            ret = components[0]
        return ret
    
    def _save(self):
        message = self._check_file()
        if message:
            return self.show_message(message, "Error")
        try:
            s = self.dom.toxml()
        except Exception as e:
            self.show_message("Error while writting: " + str(e), "Error")
        else:
            path = self.dest if self.dest else self.path
            with open(path, "w") as f:
                f.write(s)
    
    def _remove_elements(self, components):
        """ Find original implementations and remove them """
        names = set((self.URI_MAILMERGE, self.URI_PYTHONLOADER, self.URI_PYTHONSCRIPT))
        elements = []
        
        ELEMENT_NODE = components.ELEMENT_NODE
        for child in components.childNodes:
            if child.nodeType == ELEMENT_NODE:
                uri = child.getAttribute("uri")
                if uri in names:
                    names.remove(uri)
                    elements.append(child)
        for child in elements:
            components.removeChild(child)
            child.unlink()
    
    def _add_elements(self, components):
        """ Add original implementations """
        sub_dom = xml.dom.minidom.parseString(components_xml)
        elements = sub_dom.getElementsByTagName("component")
        for child in elements:
            if child.nodeType == child.ELEMENT_NODE:
                components.appendChild(child)
    
    def enable(self):
        """ Enable Python 3
            Removes original implementations from services.rdb file.
        """
        components = self._load()
        if not components:
            return
        self._remove_elements(components)
        self._save()
    
    def create_services_rdb(self):
        """ Disable Python 3
            Adds original implementations to services.rdb file.
        """
        components = self._load()
        if not components:
            return
        self._remove_elements(components)
        self._add_elements(components)
        self._save()

def Show_Information(*args):
    """ Shows information on Writer document. """
    import sys
    import ssl
    
    doc = XSCRIPTCONTEXT.getDesktop().loadComponentFromURL(
        "private:factory/swriter", "_blank", 0, ())
    
    s = str(sys.version)
    s += ssl.OPENSSL_VERSION
    s += "\nPath: \n"
    for path in sys.path:
        s += path + "\n"
    
    doc.getText().setString(s)

def Create_services_rdb(*args):
    """ Creates services.rdb file which do not contain registration about 
    default Python related components. """
    ctx = XSCRIPTCONTEXT.getComponentContext()
    dest = _get_path(ctx, save=True, default_name="services.rdb", 
            filter_names=(("RDB Files (*.rdb)", "*.rdb"),), default_filter=0)
    if not dest:
        return
    parser = Parser(ctx, dest)
    parser.enable()

def _get_path(ctx, save=False, default_name=None, filter_names=None, default_filter=None, default_dir=None):
    fp = ctx.getServiceManager().createInstanceWithContext(
        "com.sun.star.ui.dialogs.FilePicker", ctx)
    fp.initialize((10 if save else 0,))
    if filter_names:
        for filter_name, pattern in filter_names:
            fp.appendFilter(filter_name, pattern)
    if default_filter:
        fp.setCurrentFilter(filter_names[default_filter])
    if default_name:
        fp.setDefaultName(default_name)
    if default_dir:
        fp.setDisplayDirectory(default_dir)
    if fp.execute():
        dest_url = fp.getFiles()[0]
        return unohelper.fileUrlToSystemPath(dest_url)
    else:
        return

def _get_dir_path(ctx, title="Choose directory", default_dir=None):
    dp = ctx.getServiceManager().createInstanceWithContext(
        "com.sun.star.ui.dialogs.FolderPicker", ctx)
    if default_dir:
        dp.setDisplayDirectory(default_dir)
    if dp.execute():
        return unohelper.fileUrlToSystemPath(dp.getDirectory())
    else:
        return


def Create_Python_sh(*args):
    """ Creates shell script which execute python3 with environmental variables 
    to connect the office instance from the extension package. """
    ext_id = "mytools.loader.Python3"
    import sys
    import stat
    import uno
    ctx = XSCRIPTCONTEXT.getComponentContext()
    def create(name):
        return ctx.getServiceManager().createInstanceWithContext(name, ctx)
    
    dest = _get_path(ctx, save=True, default_name="python", 
            filter_names=(("All Files (*.*)", "*.*"),), default_filter=0)
    if not dest:
        return
    sd_prog = uno.fileUrlToSystemPath(create("com.sun.star.util.PathSubstitution").substituteVariables("$(prog)", True))
    
    prov = ctx.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
    ext_dir = uno.fileUrlToSystemPath(prov.getPackageLocation(ext_id))
    
    values = (("%%OFFICE_PROGRAM%%", sd_prog), ("%%EXTENSION_DIR%%", ext_dir), 
              ("%%PYVERSION%%", "{}.{}".format(sys.version_info.major, sys.version_info.minor)))
    s = PYTHON_SH_BASE
    for name, value in values:
        s = s.replace(name, value)
    
    with open(dest, "w", encoding="utf-8") as f:
        f.write(s)
    if os.path.exists(dest):
        st = os.stat(dest)
        os.chmod(dest, st.st_mode | stat.S_IEXEC)

from com.sun.star.awt.PosSize import X, Y, WIDTH, HEIGHT, POS, POSSIZE
from com.sun.star.awt.PushButtonType import OK as PushButtonType_OK, CANCEL as PushButtonType_CANCEL

from com.sun.star.awt import XActionListener

class SimpleDialog(unohelper.Base, XActionListener):
    
    MARGIN_HORI = 8
    MARGIN_VERT = 8
    VERT_SEP = 5
    HORI_SEP = 8
    CONTROL_HEIGHT = 25
    
    NAME_MAP = {
        "button": "Button", 
        "check": "CheckBox", 
        "edit": "Edit", 
        "radio": "RadioButton", 
        "label": "FixedText", 
        "line": "FixedLine", 
    }
    
    def __init__(self, ctx, data):
        self.ctx = ctx
        self.data = data
        self.dialog = None
        self._y = self.__class__.MARGIN_VERT
        self._control_width = data["width"] - 2 * self.__class__.MARGIN_HORI
        self._callbacks = {}
        self._construct()
    
    def _create(self, name):
        return self.ctx.getServiceManager().createInstanceWithContext(name, self.ctx)
    
    # context support
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.dialog.dispose()
    
    def execute(self):
        self.dialog.setVisible(True)
        return self.dialog.execute()
    
    def _construct(self):
        data = self.data
        toolkit = self._create("com.sun.star.awt.Toolkit")
        dialog = self.dialog = self._create("com.sun.star.awt.UnoControlDialog")
        dialog_model = self._create("com.sun.star.awt.UnoControlDialogModel")
        dialog.setModel(dialog_model)
        dialog.setVisible(False)
        dialog.setTitle(data["title"])
        dialog.setPosSize(0, 0, data["width"], 0, WIDTH)
        
        name_map = self.__class__.NAME_MAP
        for type, name, props in data["controls"]:
            try:
                ctrl = self._add(type, name)
                getattr(self, "_add_" + type)(ctrl, props)
                self._put_next(ctrl)
            except KeyError:
                getattr(self, "_add_" + type)(name, props)
        
        if "buttons" in data:
            self._add_command_buttons(data)
        dialog.setPosSize(0, 0, 0, self._y + self.__class__.MARGIN_VERT, HEIGHT)
        dialog.createPeer(toolkit, None)
    
    def _add(self, type, name):
        type_name = self.__class__.NAME_MAP.get(type, None)
        if type_name is None:
            raise KeyError()
        service_name = "com.sun.star.awt.UnoControl{}Model".format(type_name)
        control_model = self.dialog.getModel().createInstance(service_name)
        _name = self._get_control_name(type, name)
        self.dialog.getModel().insertByName(_name, control_model)
        return self.dialog.getControl(_name)
    
    def _get_control_name(self, type, name):
        return "{}_{}".format(type, name)
    
    def _add_callback(self, type, name, callback):
        self._callbacks[self._get_control_name(type, name)] = callback
    
    def _put_next(self, ctrl):
        ctrl.setPosSize(self.__class__.MARGIN_HORI, self._y, 
                self._control_width, self.__class__.CONTROL_HEIGHT, POSSIZE)
        self._y += self.__class__.VERT_SEP + self.__class__.CONTROL_HEIGHT
    
    def _set_label(self, ctrl, props, label=None):
        if not label:
            label = props.get("label", None)
        if label:
            #ctrl.setLabel(label)
            ctrl.getModel().Label = label
    
    def _add_radio(self, ctrl, props):
        self._set_label(ctrl, props)
        state = props.get("state", False)
        ctrl.setState(state)
    
    def _add_check(self, ctrl, props):
        self._set_label(ctrl, props)
    
    def _add_label(self, ctrl, props):
        self._set_label(ctrl, props)
    
    def _add_line(self, ctrl, props):
        self._set_label(ctrl, props)
    
    def _add_chooser(self, name, props):
        edit = self._add("edit", name + "_edit")
        button = self._add("button", name + "_button")
        self._set_label(button, props)
        self._put_next(edit)
        self._put_right(edit, button, min_size=True)
        self._set_listener(button, "button", name + "_button", props["callback"])
    
    def _add_radios(self, name, props):
        controls = []
        n = 0
        try:
            while True:
                n += 1
                label = props.get("label{}".format(n))
                sub_name = props.get("name{}".format(n))
                ctrl = self._add("radio", name + "_" + sub_name)
                self._set_label(ctrl, None, label)
                controls.append(ctrl)
        except:
            pass
        try:
            default = props["default"]
            sub_name = props[default]
            self.set_value("radio", name + "_" + sub_name, "State", 1)
            #self._get_control("radio", name + "_" + default).setState(1)
        except Exception as e:
            print(e)
        
        if len(controls) >= 2:
            previous = controls[0]
            self._put_next(previous)
            for control in controls[1:]:
                self._put_right(previous, control, align_left=True)
                previous = control
    
    def _add_buttons(self, name, props):
        BUTTON_TYPE_MAP = {"std": 0, "ok": 1, "cancel": 2, "help": 3}
        controls = []
        n = 0
        try:
            while True:
                n += 1
                label = props.get("label{}".format(n), "")
                sub_name = props["name{}".format(n)]
                button_type = props.get("type{}".format(n), "std")
                ctrl = self._add("button", name + "_" + sub_name)
                self._set_label(ctrl, None, label)
                ctrl.getModel().PushButtonType = BUTTON_TYPE_MAP[button_type]
                
                if button_type == "std":
                    callback = props.get("callable{}".format(n), None)
                    if callback:
                        self._set_listener(ctrl, "button", name + "_button", callback)
                controls.append(ctrl)
        except:
            pass
        if controls:
            self._put_next(controls[0])
            max_width = max([control.getPreferredSize().Width for control in controls])
            ps = controls[0].getPosSize()
            height = ps.Height
            y = ps.Y
            x = ps.X + ps.Width
            for control in controls[::]:
                x -= max_width
                control.setPosSize(x, y, max_width, height, POSSIZE)
                x -= self.__class__.HORI_SEP
        
    
    def _add_command_buttons(self, data):
        controls = []
        for name in data["buttons"].split(","):
            if name == "ok":
                ctrl = self._add("button", "ok")
                button_type = PushButtonType_OK
                label = "OK"
            elif name == "cancel":
                ctrl = self._add("button", "cancel")
                button_type = PushButtonType_CANCEL
                label = "Cancel"
            else:
                continue
            ctrl.getModel().PushButtonType = button_type
            self._set_label(ctrl, None, label)
            controls.append(ctrl)
        if controls:
            self._put_next(controls[0])
            max_width = max([control.getPreferredSize().Width for control in controls])
            ps = controls[0].getPosSize()
            height = ps.Height
            y = ps.Y
            x = ps.X + ps.Width
            for control in controls[::]:
                x -= max_width
                control.setPosSize(x, y, max_width, height, POSSIZE)
                x -= self.__class__.HORI_SEP
    
    def _put_right(self, base, ctrl, min_size=True, align_left=False):
        sep = self.__class__.HORI_SEP
        ps = base.getPosSize()
        if align_left:
            min_size = base.getPreferredSize()
            base.setPosSize(0, 0, min_size.Width, 0, WIDTH)
            ctrl.setPosSize(min_size.Width + sep, ps.Y, 
                        ctrl.getPreferredSize().Width, self.__class__.CONTROL_HEIGHT, POSSIZE)
        else:
            min_size = ctrl.getPreferredSize()
            base.setPosSize(0, 0, ps.Width - sep - min_size.Width, 0, WIDTH)
            ctrl.setPosSize(ps.X + base.getPosSize().Width + sep, ps.Y, 
                        min_size.Width, self.__class__.CONTROL_HEIGHT, POSSIZE)
    
    def _set_listener(self, ctrl, type, name, callback=None):
        if type == "button":
            ctrl.setActionCommand(self._get_control_name(type, name))
            ctrl.addActionListener(self)
            if callback:
                self._add_callback(type, name, callback)
    
    def _get_control(self, type, name):
        _name = self._get_control_name(type, name)
        return self.dialog.getControl(_name)
    
    def get_value(self, type, name, value_type):
        control = self._get_control(type, name)
        return control.getModel().getPropertyValue(value_type)
    
    def set_value(self, type, name, value_type, value):
        control = self._get_control(type, name)
        control.getModel().setPropertyValue(value_type, value)
    
    # XActionListener
    def disposing(self, ev):
        pass
    
    def actionPerformed(self, ev):
        cmd = ev.ActionCommand
        callback = self._callbacks.get(cmd, None)
        if callback and callable(callback):
            callback(self, cmd)


from logging import Handler

class Buffer(Handler):
    def __init__(self):
        Handler.__init__(self)
        self.lines = []
    
    def write(self, s):
        self.lines.append(s)
    
    def flush(self):
        pass
    
    def emit(self, record):
        s = str(self.format(record))
        if not s.endswith("_n"):
            s += "\n"
        self.write(s)


def Execute_2to3(*args):
    """ Executes 2to3 for specified directory """
    import traceback
    import sys
    from lib2to3.main import main
    
    ctx = XSCRIPTCONTEXT.getComponentContext()
    def create(name):
        return ctx.getServiceManager().createInstanceWithContext(name, ctx)
    
    def message(message, title):
        msgbox = create("com.sun.star.awt.Toolkit").createMessageBox(None, 0, 1, title, message)
        msgbox.execute()
    
    def write_to_writer(lines):
        import contextlib
        @contextlib.contextmanager
        def lock():
            doc.lockControllers()
            yield
            doc.unlockControllers()
        
        doc = XSCRIPTCONTEXT.getDesktop().loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
        text = doc.getText()
        with lock():
            for line in lines:
                text.getEnd().setString(line)
        cursor = text.createTextCursor()
        cursor.gotoStart(False)
        cursor.gotoEnd(True)
        cursor.ParaStyleName = "Preformatted Text"
    
    python_scripts_url = create("com.sun.star.util.PathSubstitution").substituteVariables(
                                    "$(user)/Scripts/python", True)
    
    
    def _construct_options(dialog):
        def state(type, name):
            return dialog.get_value(type, name, "State")
        
        args = []
        path = dialog.get_value("edit", "input_edit", "Text")
        if not os.path.exists(path):
            raise Exception("Choose file or directory")
        args.append(path)
        if state("check", "print"):
            args.append("--print-function")
        if state("check", "verbose"):
            args.append("--verbose")
        if state("check", "nodiffs"):
            args.append("--no-diffs")
        if state("check", "writeback"):
            args.append("--write")
        if state("check", "nobackup"):
            args.append("--nobackups")
        if state("check", "dirout"):
            path = dialog.get_value("edit", "output_edit", "Text")
            if not path:
                raise Exception("Choose directory to write files")
            args.append("--output-dir=" + path)
        if state("check", "writealso"):
            args.append("--write-unchanged-files")
        return args
    
    
    def execute_2to3(dialog, cmd):
        try:
            args = _construct_options(dialog)
        except Exception as e:
            message(str(e), "Error")
            return
        b = Buffer()
        import logging
        logger = logging.getLogger("RefactoringTool")
        logger.addHandler(b)
        
        _stdout = sys.stdout
        _stderr = sys.stderr
        sys.stdout = b
        sys.stderr = b

        try:
            sys.argv = args
            main("lib2to3.fixes", args=args)
        except:
            traceback.print_exc()
        finally:
            sys.stdout = _stdout
            sys.stderr = _stderr
            del sys.argv
            logger.removeHandler(b)
        write_to_writer(b.lines)
    
    
    def choose_input(dialog, cmd):
        if dialog.get_value("radio", "target_file", "State"):
            path = _get_path(ctx, save=False, default_dir=python_scripts_url)
        elif dialog.get_value("radio", "target_dir", "State"):
            path = _get_dir_path(ctx, default_dir=python_scripts_url)
        if path:
            dialog.set_value("edit", "input_edit", "Text", path)
    
    def choose_output(dialog, cmd):
        path = _get_dir_path(ctx, default_dir=python_scripts_url)
        if path:
            dialog.set_value("edit", "output_edit", "Text", path)
    
    args = []
    
    dialog_data = {
        "title": "Execute 2to3", 
        "width": 550, 
        "controls": [
            ("line", "inlabel", {"label": "Input file or directory", }), 
            ("radios", "target", {"label1": "File", "label2": "Directory contents", "name1": "file", "name2": "dir", "default": "name1",}), 
            ("chooser", "input",   {"label": "Select", "callback": choose_input}), 
            
            ("line", "opline", {"label": "Fix options"}), 
            ("check", "print",     {"label": "Modify the grammar so that print() is a function (--print-function)"}), 
            ("check", "verbose", {"label": "More verbose logging (--verbose)", }), 
            ("check", "nodiffs", {"label": "Don't show diffs of the refactoring (--no-diffs)", }), 
            
            ("line", "outopline", {"label": "Output options"}), 
            ("check", "writeback", {"label": "Write back modified files (-w/--write)", }), 
            ("check", "nobackup", {"label": "Don't write backups for modified files (-n/--nobackups)", }), 
            
            ("line", "outlabel", {"label": "Output directory", }), 
            ("check", "dirout", {"label": "Put output files in this directory. Choose both -w and -n if you need output.", }), 
            ("chooser", "output", {"label": "Select", "callback": choose_output}), 
            ("check", "writealso", {"label": "Also write files even if no changes were required (--write-unchanged-files)", }), 
            
            ("line", "endline", {}),
            ("buttons", "cmds", {"label1": "Close", "label2": "~Execute", "name1": "close", "name2": "execute", "type1": "cancel", "callable2": execute_2to3, }), 
        ]
    }
    with SimpleDialog(ctx, dialog_data) as d:
        d.execute()


g_exportedScripts = Create_services_rdb, Show_Information, Create_Python_sh, Execute_2to3
