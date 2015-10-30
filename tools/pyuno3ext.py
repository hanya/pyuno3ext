
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

def _get_path(ctx, save=False, default_name=None, filter_names=None, default_filter=None):
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
    if fp.execute():
        dest_url = fp.getFiles()[0]
        return unohelper.fileUrlToSystemPath(dest_url)
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

g_exportedScripts = Create_services_rdb, Show_Information, Create_Python_sh
