
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
    ctx = XSCRIPTCONTEXT.getComponentContext()
    dest = _get_path(ctx, save=True, default_name="services.rdb", 
            filter_names=(("RDB Files (*rdb)", "*.rdb"),), default_filter=0)
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

g_exportedScripts = Create_services_rdb, Show_Information
