# *************************************************************
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
# *************************************************************

# XScript implementation for python
import uno
import unohelper
import sys
import os
import time
import ast
import platform

try:
    unicode
except NameError:
    unicode = str

class LogLevel:
    NONE = 0   # production level
    ERROR = 1  # for script developers
    DEBUG = 2  # for script framework developers

PYSCRIPT_LOG_ENV = "PYSCRIPT_LOG_LEVEL"
PYSCRIPT_LOG_STDOUT_ENV = "PYSCRIPT_LOG_STDOUT"

# Configuration ----------------------------------------------------
LogLevel.use = LogLevel.NONE
if os.environ.get(PYSCRIPT_LOG_ENV) == "ERROR":
    LogLevel.use = LogLevel.ERROR
elif os.environ.get(PYSCRIPT_LOG_ENV) == "DEBUG":
    LogLevel.use = LogLevel.DEBUG

# True, writes to stdout (difficult on windows)
# False, writes to user/Scripts/python/log.txt
LOG_STDOUT = os.environ.get(PYSCRIPT_LOG_STDOUT_ENV, "1") != "0"

ENABLE_EDIT_DIALOG = False                    # offers a minimal editor for editing.
#-------------------------------------------------------------------

def encfile(uni):
    if not isinstance(uni, str):
        return uni.encode(sys.getfilesystemencoding())
    return uni

def lastException2String():
    excType, excInstance, excTraceback = sys.exc_info()
    ret = str(excType) + ": " + str(excInstance) + "\n" + \
          uno._uno_extract_printable_stacktrace( excTraceback )
    return ret

def logLevel2String(level):
    ret = " NONE"
    if level == LogLevel.ERROR:
        ret = "ERROR"
    elif level >= LogLevel.DEBUG:
        ret = "DEBUG"
    return ret

def getLogTarget():
    ret = sys.stdout
    if not LOG_STDOUT:
        try:
            pathSubst = uno.getComponentContext().getServiceManager().createInstance(
                "com.sun.star.util.PathSubstitution")
            userInstallation =  pathSubst.getSubstituteVariableValue("user")
            if len(userInstallation) > 0:
                systemPath = uno.fileUrlToSystemPath( userInstallation + "/Scripts/python/log.txt")
                ret = open(systemPath , "a")
        except Exception as e:
            print("Exception during creation of pythonscript logfile: " + lastException2String() + "\n, delagating log to stdout\n")
    return ret

class Logger(LogLevel):
    def __init__(self , target):
        self.target = target

    def isDebugLevel(self):
        return self.use >= self.DEBUG

    def debug(self, msg):
        if self.isDebugLevel():
            self.log(self.DEBUG, msg)

    def isErrorLevel(self):
        return self.use >= self.ERROR

    def error(self, msg):
        if self.isErrorLevel():
            self.log(self.ERROR, msg)

    def log(self, level, msg):
        if self.use >= level:
            try:
                self.target.write(
                    "{} [{}] {}\n".format(time.asctime(), logLevel2String(level), encfile(msg)))
                self.target.flush()
            except Exception as e:
                print("Error during writing to stdout: " +lastException2String() + "\n")

log = Logger(getLogTarget())

log.debug("pythonscript loading")

#from com.sun.star.lang import typeOfXServiceInfo, typeOfXTypeProvider
from com.sun.star.lang import XServiceInfo
from com.sun.star.io import IOException
from com.sun.star.ucb import CommandAbortedException, XCommandEnvironment, XProgressHandler, Command
from com.sun.star.task import XInteractionHandler
from com.sun.star.beans import XPropertySet, Property
from com.sun.star.container import XNameContainer
from com.sun.star.xml.sax import XDocumentHandler, InputSource
from com.sun.star.uno import Exception as UnoException, RuntimeException
from com.sun.star.script import XInvocation
from com.sun.star.awt import XActionListener

from com.sun.star.script.provider import XScriptProvider, XScript, XScriptContext, ScriptFrameworkErrorException
from com.sun.star.script.browse import XBrowseNode
from com.sun.star.script.browse.BrowseNodeTypes import SCRIPT, CONTAINER, ROOT
from com.sun.star.util import XModifyListener

LANGUAGENAME = "Python"
GLOBAL_SCRIPTCONTEXT_NAME = "XSCRIPTCONTEXT"
CALLABLE_CONTAINER_NAME =  "g_exportedScripts"

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_implName = "org.openoffice.pyuno.LanguageScriptProviderFor" + LANGUAGENAME



BLOCK_SIZE = 65536
def readTextFromStream(inputStream):
    # read the file
    code = uno.ByteSequence(bytes() if sys.version_info.major >= 3 else "")
    while True:
        read,out = inputStream.readBytes(None, BLOCK_SIZE)
        code = code + out
        if read < BLOCK_SIZE:
            break
    return code.value

def toIniName(str):
    return str + (".ini" if platform.system().lower() == "windows" else "rc")


""" definition: storageURI is the system dependent, absolute file url, where the script is stored on disk
                scriptURI is the system independent uri
"""
class MyUriHelper:

    def __init__(self, ctx, location):
        self.s_UriMap = \
        { "share" : "vnd.sun.star.expand:${$OOO_BASE_DIR/program/" +  toIniName("bootstrap") + "::BaseInstallation}/share/Scripts/python" , \
          "share:uno_packages" : "vnd.sun.star.expand:$UNO_SHARED_PACKAGES_CACHE/uno_packages", \
          "user" : "vnd.sun.star.expand:${$OOO_BASE_DIR/program/" + toIniName("bootstrap") + "::UserInstallation}/user/Scripts/python" , \
          "user:uno_packages" : "vnd.sun.star.expand:$UNO_USER_PACKAGES_CACHE/uno_packages" }
        self.m_uriRefFac = ctx.getServiceManager().createInstanceWithContext("com.sun.star.uri.UriReferenceFactory", ctx)
        if location.startswith("vnd.sun.star.tdoc"):
            self.m_baseUri = location + "/Scripts/python"
            self.m_scriptUriLocation = "document"
        else:
            self.m_baseUri = expandUri(self.s_UriMap[location])
            self.m_scriptUriLocation = location
        log.debug("initialized urihelper with baseUri=" + self.m_baseUri + ",m_scriptUriLocation=" + self.m_scriptUriLocation)

    def getRootStorageURI(self):
        return self.m_baseUri

    def getStorageURI(self, scriptURI):
        return self.scriptURI2StorageUri(scriptURI)

    def getScriptURI(self, storageURI):
        return self.storageURI2ScriptUri(storageURI)

    def storageURI2ScriptUri(self, storageURI):
        if not storageURI.startswith(self.m_baseUri):
            message = "pythonscript: storage uri '" + storageURI + "' not in base uri '" + self.m_baseUri + "'"
            log.debug(message)
            raise RuntimeException(message)
        
        ret = "vnd.sun.star.script:{}?language={}&location={}".format(
                storageURI[len(self.m_baseUri)+1:].replace("/","|"), 
                LANGUAGENAME, self.m_scriptUriLocation)
        log.debug("converting storageURI=" + storageURI + " to scriptURI=" + ret)
        return ret

    def scriptURI2StorageUri(self, scriptURI):
        try:
            myUri = self.m_uriRefFac.parse(scriptURI)
            ret = self.m_baseUri + "/" + myUri.getName().replace( "|", "/" )
            log.debug("converting scriptURI="+scriptURI + " to storageURI=" + ret)
            return ret
        except UnoException as e:
            log.error("error during converting scriptURI=" + scriptURI + ": " + e.Message)
            raise RuntimeException( "pythonscript:scriptURI2StorageUri: " +e.getMessage(), None)
        except Exception as e:
            log.error("error during converting scriptURI=" + scriptURI + ": " + str(e))
            raise RuntimeException( "pythonscript:scriptURI2StorageUri: " + str(e), None)


class ModuleEntry:
    def __init__(self, lastRead, module):
        self.lastRead = lastRead
        self.module = module

def hasChanged(oldDate, newDate):
    return newDate.Year > oldDate.Year or \
           newDate.Month > oldDate.Month or \
           newDate.Day > oldDate.Day or \
           newDate.Hours > oldDate.Hours or \
           newDate.Minutes > oldDate.Minutes or \
           newDate.Seconds > oldDate.Seconds or \
           newDate.HundredthSeconds > oldDate.HundredthSeconds

def ensureSourceState(code):
    if isinstance(code, str):
        if not code.endswith("\n"):
            code = code + "\n"
        code = code.replace("\r", "")
    else:
        if not code.endswith(bytes("\n", "utf-8")):
            code = code + bytes("\n", "utf-8")
        code = code.replace(bytes("\r", "utf-8"), bytes("", "utf-8"))
    return code


def checkForPythonPathBesideScript(url):
    if url.startswith("file:"):
        path = unohelper.fileUrlToSystemPath(url + "/pythonpath.zip");
        log.log(LogLevel.DEBUG, "checking for existence of " + path)
        if 1 == os.access(encfile(path), os.F_OK) and not path in sys.path:
            log.log(LogLevel.DEBUG, "adding " + path + " to sys.path")
            sys.path.append(path)

        path = unohelper.fileUrlToSystemPath(url + "/pythonpath");
        log.log(LogLevel.DEBUG,  "checking for existence of " + path)
        if 1 == os.access(encfile(path), os.F_OK) and not path in sys.path:
            log.log(LogLevel.DEBUG, "adding " + path + " to sys.path")
            sys.path.append(path)


class ScriptContext(unohelper.Base):
    def __init__(self, ctx, doc, inv):
        self.ctx = ctx
        self.doc = doc
        self.inv = inv

   # XScriptContext
    def getDocument(self):
        if self.doc:
            return self.doc
        return self.getDesktop().getCurrentComponent()

    def getDesktop(self):
        return self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

    def getComponentContext(self):
        return self.ctx

    def getInvocationContext(self):
        return self.inv


class ProviderContext:
    def __init__(self, storageType, sfa, uriHelper, scriptContext):
        self.storageType = storageType
        self.sfa = sfa
        self.uriHelper = uriHelper
        self.scriptContext = scriptContext
        self.modules = {}
        self.rootUrl = None
        self.mapPackageName2Path = None

    def getTransientPartFromUrl(self, url):
        rest = url.replace(self.rootUrl, "", 1).replace("/", "", 1)
        return rest[0:rest.find("/")]

    def getPackageNameFromUrl(self, url):
        rest = url.replace(self.rootUrl, "", 1).replace("/", "", 1)
        start = rest.find("/") +1
        return rest[start:rest.find("/", start)]

    def removePackageByUrl(self, url):
        for name, package in self.mapPackageName2Path.items():
            if url in package.pathes:
                self.mapPackageName2Path.pop(name)
                break

    def addPackageByUrl(self, url):
        packageName = self.getPackageNameFromUrl(url)
        transientPart = self.getTransientPartFromUrl(url)
        log.debug("addPackageByUrl : " + packageName + ", " + transientPart + "("+url+")" + ", rootUrl=" + self.rootUrl)
        if packageName in self.mapPackageName2Path:
            package = self.mapPackageName2Path[packageName]
            package.pathes = package.pathes + (url,)
        else:
            package = Package((url,), transientPart)
            self.mapPackageName2Path[packageName] = package

    def isUrlInPackage(self, url):
        for package in self.mapPackageName2Path.values():
            if url in package.pathes:
                return True
        return False

    def setPackageAttributes(self, mapPackageName2Path, rootUrl):
        self.mapPackageName2Path = mapPackageName2Path
        self.rootUrl = rootUrl

    def getPersistentUrlFromStorageUrl(self, url):
        # package name is the second directory
        ret = url
        if self.rootUrl:
            pos = len(self.rootUrl) +1
            ret = url[0:pos]+url[url.find("/",pos)+1:]
        log.debug("getPersistentUrlFromStorageUrl " + url +  " -> "+ ret)
        return ret

    def getStorageUrlFromPersistentUrl(self, url):
        ret = url
        if self.rootUrl:
            pos = len(self.rootUrl)+1
            packageName = url[pos:url.find("/",pos+1)]
            package = self.mapPackageName2Path[packageName]
            ret = url[0:pos]+ package.transientPathElement + "/" + url[pos:]
        log.debug("getStorageUrlFromPersistentUrl " + url + " -> "+ ret)
        return ret

    def getFuncsByUrl(self, url):
        src = readTextFromStream(self.sfa.openFileRead(url))
        checkForPythonPathBesideScript(url[0:url.rfind('/')])
        src = ensureSourceState(src)

        allFuncs = []
        g_exportedScripts = []

        a = ast.parse(src, url)

        if isinstance(a, ast.Module):
            for node in a.body:
                if isinstance(node, ast.FunctionDef):
                    allFuncs.append(node.name)
                elif isinstance(node, ast.Assign):
                    is_exported = False
                    for subnode in node.targets:
                        if isinstance(subnode, ast.Name) and \
                            subnode.id == "g_exportedScripts":
                            is_exported = True
                            break
                    if is_exported:
                        value_node = node.value
                        if isinstance(value_node, ast.List) or \
                            isinstance(value_node, ast.Tuple):
                            for elt in value_node.elts:
                                if isinstance(elt, ast.Str):
                                    g_exportedScripts.append(elt.s)
                                elif isinstance(elt, ast.Name):
                                    g_exportedScripts.append(elt.id)
                        elif isinstance(value_node, ast.Str):
                            g_exportedScripts.append(value_node.s)
                        elif isinstance(value_node, ast.Name):
                            g_exportedScripts.append(value_node.id)
                        return g_exportedScripts
        return allFuncs

    def getModuleByUrl(self, url):
        entry =  self.modules.get(url)
        load = True
        lastRead = self.sfa.getDateTimeModified(url)
        if entry:
            if hasChanged(entry.lastRead, lastRead):
                log.debug("file " + url + " has changed, reloading")
            else:
                load = False

        if load:
            log.debug("opening >" + url + "<")

            src = readTextFromStream(self.sfa.openFileRead(url))
            checkForPythonPathBesideScript(url[0:url.rfind('/')])
            src = ensureSourceState(src)

            # execute the module
            entry = ModuleEntry(lastRead, type(sys)("ooo_script_framework"))
            entry.module.__dict__[GLOBAL_SCRIPTCONTEXT_NAME] = self.scriptContext
            
            code = None
            if url.startswith("file:"):
                code = compile(src, encfile(uno.fileUrlToSystemPath(url)), "exec")
            else:
                code = compile(src, url, "exec")
            exec(code, entry.module.__dict__)
            entry.module.__file__ = url
            self.modules[url] = entry
            log.debug("mapped " + url + " to " + str(entry.module))
        return  entry.module

#--------------------------------------------------
def isScript(candidate):
    ret = False
    if isinstance(candidate, type(isScript)):
        ret = True
    return ret

#-------------------------------------------------------
class BrowseNodeBase(unohelper.Base, XBrowseNode):
    
    NODE_TYPE = CONTAINER
    
    def __init__(self, provCtx, uri, name):
        self.provCtx = provCtx
        self.uri = uri
        self.name = name
    
    # XBrowseNode
    def getName(self):
        return self.name
    
    def getChildNodes(self):
        return ()
    
    def hasChildNodes(self):
        return False
    
    def getType(self):
        return self.NODE_TYPE


class ScriptBrowseNode(BrowseNodeBase, XPropertySet, XInvocation, XActionListener):
    
    NODE_TYPE = SCRIPT
    
    def __init__(self, provCtx, uri, fileName, name):
        super().__init__(provCtx, uri, name)
        self.fileName = fileName
    
    def getPropertyValue(self, name):
        ret = None
        try:
            if name == "URI":
                ret = self.provCtx.uriHelper.getScriptURI(
                    self.provCtx.getPersistentUrlFromStorageUrl(self.uri + "$" + self.name))
            elif name == "Editable" and ENABLE_EDIT_DIALOG:
                ret = not self.provCtx.sfa.isReadOnly(self.uri)

            log.debug("ScriptBrowseNode.getPropertyValue called for " + name + ", returning " + str(ret))
        except Exception as e:
            log.error("ScriptBrowseNode.getPropertyValue error " + lastException2String())
            raise

        return ret
    def setPropertyValue(self, name, value):
        log.debug("ScriptBrowseNode.setPropertyValue called " + name + "=" + str(value))
    def getPropertySetInfo(self):
        log.debug("ScriptBrowseNode.getPropertySetInfo called ")
        return None

    def getIntrospection(self):
        return None

    def invoke(self, name, params, outparamindex, outparams):
        if name == "Editable":
            servicename = "com.sun.star.awt.DialogProvider"
            ctx = self.provCtx.scriptContext.getComponentContext()
            dlgprov = ctx.getServiceManager().createInstanceWithContext(
                servicename, ctx)

            self.editor = dlgprov.createDialog(
                "vnd.sun.star.script:" +
                "ScriptBindingLibrary.MacroEditor?location=application")

            code = readTextFromStream(self.provCtx.sfa.openFileRead(self.uri))
            code = ensureSourceState(code)
            self.editor.getControl("EditorTextField").setText(code)

            self.editor.getControl("RunButton").setActionCommand("Run")
            self.editor.getControl("RunButton").addActionListener(self)
            self.editor.getControl("SaveButton").setActionCommand("Save")
            self.editor.getControl("SaveButton").addActionListener(self)

            self.editor.execute()

        return None

    def actionPerformed(self, event):
        try:
            if event.ActionCommand == "Run":
                code = self.editor.getControl("EditorTextField").getText()
                code = ensureSourceState( code )
                mod = type(sys)("ooo_script_framework")
                mod.__dict__[GLOBAL_SCRIPTCONTEXT_NAME] = self.provCtx.scriptContext
                exec(code, mod.__dict__)
                values = mod.__dict__.get(CALLABLE_CONTAINER_NAME, None)
                if not values:
                    values = list(mod.__dict__.values())

                for i in values:
                    if isScript(i):
                        i()
                        break

            elif event.ActionCommand == "Save":
                toWrite = uno.ByteSequence(
                    str(
                    self.editor.getControl("EditorTextField").getText().encode(
                    sys.getdefaultencoding())))
                copyUrl = self.uri + ".orig"
                self.provCtx.sfa.move(self.uri, copyUrl)
                out = self.provCtx.sfa.openFileWrite(self.uri)
                out.writeBytes(toWrite)
                out.close()
                self.provCtx.sfa.kill(copyUrl)
#                log.debug("Save is not implemented yet")
#                text = self.editor.getControl("EditorTextField").getText()
#                log.debug("Would save: " + text)
        except Exception as e:
            # TODO: add an error box here !
            log.error(lastException2String())


    def setValue(self, name, value):
        return None

    def getValue(self, name):
        return None

    def hasMethod(self, name):
        return False

    def hasProperty(self, name):
        return False


#-------------------------------------------------------
class FileBrowseNode(BrowseNodeBase):
    def __init__(self, provCtx, uri, name):
        super().__init__(provCtx, uri, name)
        self.func_names = None
    
    def getChildNodes(self):
        ret = ()
        try:
            self.func_names = self.provCtx.getFuncsByUrl(self.uri)
            ret = tuple([ScriptBrowseNode(self.provCtx, self.uri, self.name, func_name)
                                for func_name in self.func_names])
            log.debug("returning {} ScriptChildNodes on {}".format(len(ret), self.uri))
        except Exception as e:
            text = lastException2String()
            log.error("Error while evaluating " + self.uri + ":" + text)
            raise
        return ret

    def hasChildNodes(self):
        try:
            return len(self.getChildNodes()) > 0
        except:
            return False


class DirBrowseNode(BrowseNodeBase):
    def __init__(self, provCtx, uri, name):
        super().__init__(provCtx, uri, name)

    def getChildNodes(self):
        try:
            log.debug("DirBrowseNode.getChildNodes called for " + self.uri)
            contents = self.provCtx.sfa.getFolderContents(self.uri, True)
            browseNodeList = []
            for url in contents:
                if self.provCtx.sfa.isFolder(url) and not url.endswith("/pythonpath"):
                    log.debug("adding DirBrowseNode " + url)
                    browseNodeList.append(DirBrowseNode(self.provCtx, url, url[url.rfind("/")+1:]))
                elif url.endswith(".py"):
                    log.debug("adding filenode " + url)
                    browseNodeList.append(FileBrowseNode(self.provCtx, url, url[url.rfind("/")+1:-3]))
            return tuple(browseNodeList)
        except Exception as e:
            text = lastException2String()
            log.error("DirBrowseNode error: " + str(e) + " while evaluating " + self.uri)
            log.error(text)
            return ()

    def hasChildNodes(self):
        return True


class ManifestHandler(XDocumentHandler, unohelper.Base):
    def __init__(self, rootUrl):
        self.rootUrl = rootUrl

    def startDocument(self):
        self.urlList = []

    def endDocument(self):
        pass

    def startElement(self, name, attlist):
        if name == "manifest:file-entry":
            if attlist.getValueByName("manifest:media-type") == "application/vnd.sun.star.framework-script":
                self.urlList.append(
                    self.rootUrl + "/" + attlist.getValueByName("manifest:full-path"))

    def endElement(self, name):
        pass

    def characters (self, chars):
        pass

    def ignoreableWhitespace(self, chars):
        pass

    def setDocumentLocator(self, locator):
        pass

def isPyFileInPath(sfa, path):
    ret = False
    contents = sfa.getFolderContents(path, True)
    for i in contents:
        if sfa.isFolder(i):
            ret = isPyFileInPath(sfa, i)
        else:
            if i.endswith(".py"):
                ret = True
        if ret:
            break
    return ret

# extracts META-INF directory from
def getPathesFromPackage( rootUrl, sfa ):
    ret = ()
    try:
        fileUrl = rootUrl + "/META-INF/manifest.xml"
        inputStream = sfa.openFileRead(fileUrl)
        parser = uno.getComponentContext().getServiceManager().createInstance("com.sun.star.xml.sax.Parser")
        handler = ManifestHandler(rootUrl)
        parser.setDocumentHandler(handler)
        parser.parseStream(InputSource(inputStream, "", fileUrl, fileUrl))
        for i in tuple(handler.urlList):
            if not isPyFileInPath(sfa, i):
                handler.urlList.remove(i)
        ret = tuple(handler.urlList)
    except UnoException as e:
        text = lastException2String()
        log.debug("getPathesFromPackage " + fileUrl + " Exception: " + text)
        pass
    return ret


class Package:
    def __init__(self, pathes, transientPathElement):
        self.pathes = pathes
        self.transientPathElement = transientPathElement

class DummyInteractionHandler(unohelper.Base, XInteractionHandler):
    def handle(self, event):
        log.debug("pythonscript: DummyInteractionHandler.handle " + str(event))

class DummyProgressHandler(unohelper.Base, XProgressHandler):
    def push(self, status):
        log.debug("pythonscript: DummyProgressHandler.push " + str(status))
    def update(self, status):
        log.debug("pythonscript: DummyProgressHandler.update " + str(status))
    def pop(self):
        log.debug("pythonscript: DummyProgressHandler.push " + str(event))

class CommandEnvironment(unohelper.Base, XCommandEnvironment):
    def __init__(self):
        self.progressHandler = DummyProgressHandler()
        self.interactionHandler = DummyInteractionHandler()
    def getInteractionHandler(self):
        return self.interactionHandler
    def getProgressHandler(self):
        return self.progressHandler

#maybe useful for debugging purposes
#class ModifyListener( unohelper.Base, XModifyListener ):
#    def __init__( self ):
#        pass
#    def modified( self, event ):
#        log.debug( "pythonscript: ModifyListener.modified " + str( event ) )
#    def disposing( self, event ):
#        log.debug( "pythonscript: ModifyListener.disposing " + str( event ) )

def getModelFromDocUrl(ctx, url):
    """Get document model from document url."""
    doc = None
    args = ("Local", "Office")
    ucb = ctx.getServiceManager().createInstanceWithArgumentsAndContext(
        "com.sun.star.ucb.UniversalContentBroker", args, ctx)
    identifier = ucb.createContentIdentifier(url)
    content = ucb.queryContent(identifier)
    p = Property()
    p.Name = "DocumentModel"
    p.Handle = -1

    c = Command("getPropertyValues", -1, uno.Any("[]com.sun.star.beans.Property", (p,)))

    env = CommandEnvironment()
    try:
        ret = content.execute(c, 0, env)
        doc = ret.getObject(1, None)
    except Exception as e:
        log.isErrorLevel() and log.error("getModelFromDocUrl: %s" % url)
    return doc

def mapStorageType2PackageContext(storageType):
    ret = storageType
    if storageType == "share:uno_packages":
        ret = "shared"
    elif storageType == "user:uno_packages":
        ret = "user"
    return ret

def getPackageName2PathMap(sfa, storageType):
    ret = {}
    extension_manager = uno.getComponentContext().getValueByName(
        "/singletons/com.sun.star.deployment.ExtensionManager")
    log.debug("pythonscript: getPackageName2PathMap start getDeployedPackages")
    packages = extension_manager.getDeployedExtensions(
                mapStorageType2PackageContext(storageType), 
                extension_manager.createAbortChannel(), CommandEnvironment())
    log.debug("pythonscript: getPackageName2PathMap end getDeployedPackages (" + str(len(packages)) + ")")

    for package in packages:
        log.debug("inspecting package " + package.getName() + "(" + package.getIdentifier().Value + ")")
        transientPathElement = penultimateElement(package.getURL())
        uri = expandUri(package.getURL())
        pathes = getPathesFromPackage(uri, sfa)
        if len(pathes) > 0:
            # map package name to url, we need this later
            log.isErrorLevel() and log.error("adding Package " + transientPathElement + " " + str(pathes))
            ret[lastElement(uri)] = Package(pathes, transientPathElement)
    return ret

def penultimateElement(aStr):
    lastSlash = aStr.rindex("/")
    penultimateSlash = aStr.rindex("/", 0, lastSlash-1)
    return  aStr[penultimateSlash+1:lastSlash]

def lastElement(aStr):
    return aStr[aStr.rfind("/")+1:]

class PackageBrowseNode(BrowseNodeBase):
    def __init__(self, provCtx, uri, name):
        super().__init__(provCtx, uri, name)
    
    def getChildNodes(self):
        browseNodeList = []
        for name, package in self.provCtx.mapPackageName2Path.items():
            if len(package.pathes) == 1:
                browseNodeList.append(
                    DirBrowseNode(self.provCtx, package.pathes[0], name))
            else:
                for path in package.pathes:
                    browseNodeList.append(
                        DirBrowseNode(self.provCtx, path, name + "." + lastElement(path)))
        return tuple(browseNodeList)

    def hasChildNodes(self):
        return len(self.provCtx.mapPackageName2Path) > 0


class PythonScript(unohelper.Base, XScript):
    def __init__(self, func, mod):
        self.func = func
        self.mod = mod
    def invoke(self, args, out, outindex):
        log.debug("PythonScript.invoke " + str(args))
        try:
            ret = self.func(*args)
        except UnoException as e:
            # UNO Exception continue to fly ...
            text = lastException2String()
            complete = "Error during invoking function " + \
                str(self.func.__name__) + " in module " + \
                self.mod.__file__ + " (" + text + ")"
            log.debug(complete)
            # some people may beat me up for modifying the exception text,
            # but otherwise office just shows
            # the type name and message text with no more information,
            # this is really bad for most users.
            e.Message = e.Message + " (" + complete + ")"
            raise
        except Exception as e:
            # General python exception are converted to uno RuntimeException
            text = lastException2String()
            complete = "Error during invoking function " + \
                str(self.func.__name__) + " in module " + \
                self.mod.__file__ + " (" + text + ")"
            log.debug(complete)
            raise RuntimeException(complete, self)
        log.debug("PythonScript.invoke ret = " + str(ret))
        return ret, (), ()

def expandUri(uri):
    if uri.startswith("vnd.sun.star.expand:"):
        uri = uri.replace("vnd.sun.star.expand:", "", 1)
        uri = uno.getComponentContext().getByName(
                    "/singletons/com.sun.star.util.theMacroExpander").expandMacros(uri)
    if uri.startswith("file:"):
        uri = uno.absolutize("", uri)   # necessary to get rid of .. in uri
    return uri

#--------------------------------------------------------------
class PythonScriptProvider(BrowseNodeBase, XScriptProvider, XNameContainer):
    def __init__(self, ctx, *args):
        super().__init__(None, "", LANGUAGENAME)
        if log.isDebugLevel():
            mystr = ""
            for i in args:
                if len(mystr) > 0:
                    mystr = mystr +","
                mystr = mystr + str(i)
            log.debug("Entering PythonScriptProvider.ctor" + mystr)

        doc = None
        inv = None
        storageType = ""

        if isinstance(args[0], str):
            storageType = args[0]
            if storageType.startswith("vnd.sun.star.tdoc"):
                doc = getModelFromDocUrl(ctx, storageType)
        else:
            inv = args[0]
            try:
                doc = inv.ScriptContainer
                content = ctx.getServiceManager().createInstanceWithContext(
                    "com.sun.star.frame.TransientDocumentsDocumentContentFactory",
                    ctx).createDocumentContent(doc)
                storageType = content.getIdentifier().getContentIdentifier()
            except Exception as e:
                text = lastException2String()
                log.error(text)

        try:
            urlHelper = MyUriHelper(ctx, storageType)
            log.debug("got urlHelper " + str(urlHelper))

            rootUrl = expandUri(urlHelper.getRootStorageURI())
            log.debug(storageType + " transformed to " + rootUrl)

            ucbService = "com.sun.star.ucb.SimpleFileAccess"
            sfa = ctx.getServiceManager().createInstanceWithContext(ucbService, ctx)
            if not sfa:
                log.debug("PythonScriptProvider couldn't instantiate " + ucbService)
                raise RuntimeException(
                    "PythonScriptProvider couldn't instantiate " + ucbService, self)
            self.provCtx = ProviderContext(
                storageType, sfa, urlHelper, ScriptContext(ctx, doc, inv))
                
            if storageType.endswith(":uno_packages"):
                mapPackageName2Path = getPackageName2PathMap(sfa, storageType)
                self.provCtx.setPackageAttributes(mapPackageName2Path, rootUrl)
                self.dirBrowseNode = PackageBrowseNode(self.provCtx, rootUrl, LANGUAGENAME)
            else:
                self.dirBrowseNode = DirBrowseNode(self.provCtx, rootUrl, LANGUAGENAME)

        except Exception as e:
            text = lastException2String()
            log.debug("PythonScriptProvider could not be instantiated because of : " + text)
            raise e

    def getChildNodes(self):
        return self.dirBrowseNode.getChildNodes()

    def hasChildNodes(self):
        return self.dirBrowseNode.hasChildNodes()

    def getScript(self, scriptUri):
        try:
            log.debug("getScript " + scriptUri + " invoked")

            storageUri = self.provCtx.getStorageUrlFromPersistentUrl(
                self.provCtx.uriHelper.getStorageURI(scriptUri));
            log.debug("getScript: storageUri = " + storageUri)
            fileUri = storageUri[0:storageUri.find("$")]
            funcName = storageUri[storageUri.find("$")+1:len(storageUri)]

            mod = self.provCtx.getModuleByUrl(fileUri)
            log.debug(" got mod " + str(mod))

            func = mod.__dict__[funcName]

            log.debug("got func " + str(func))
            return PythonScript(func, mod)
        except Exception as e:
            text = lastException2String()
            log.error(text)
            raise ScriptFrameworkErrorException(text, self, scriptUri, LANGUAGENAME, 0)


    # XServiceInfo
    def getSupportedServices(self):
        return g_ImplementationHelper.getSupportedServices(g_implName)

    def supportsService(self, ServiceName):
        return g_ImplementationHelper.supportsService(g_implName, ServiceName)

    def getImplementationName(self):
        return g_implName
    
    # XNameContainer
    def getByName(self, name):
        log.debug("getByName called" + str(name))
        return None

    def getElementNames(self):
        log.debug("getElementNames called")
        return ()

    def hasByName(self, name):
        try:
            log.debug("hasByName called " + str(name))
            uri = expandUri(name)
            ret = self.provCtx.isUrlInPackage(uri)
            log.debug("hasByName " + uri + " " + str(ret))
            return ret
        except Exception as e:
            text = lastException2String()
            log.debug("Error in hasByName:" +  text)
            return False

    def removeByName(self, name):
        log.debug("removeByName called" + str(name))
        uri = expandUri(name)
        if self.provCtx.isUrlInPackage(uri):
            self.provCtx.removePackageByUrl(uri)
        else:
            log.debug("removeByName unknown uri " + str(name) + ", ignoring")
            raise NoSuchElementException(uri + "is not in package" , self)
        log.debug("removeByName called" + str(uri) + " successful")

    def insertByName(self, name, value):
        log.debug("insertByName called " + str(name) + " " + str(value))
        uri = expandUri(name)
        if isPyFileInPath(self.provCtx.sfa, uri):
            self.provCtx.addPackageByUrl(uri)
        else:
            # package is no python package ...
            log.debug("insertByName: no python files in " + str( uri ) + ", ignoring")
            raise IllegalArgumentException(uri + " does not contain .py files", self, 1)
        log.debug("insertByName called " + str(uri) + " successful")

    def replaceByName(self, name, value):
        log.debug("replaceByName called " + str(name) + " " + str(value))
        self.removeByName(name)
        self.insertByName(name)
        log.debug("replaceByName called" + str(uri) + " successful")

    def getElementType( self ):
        log.debug("getElementType called")
        return uno.getTypeByName("void")

    def hasElements(self):
        log.debug("hasElements got called")
        return False

g_ImplementationHelper.addImplementation( \
        PythonScriptProvider, g_implName, \
    ("com.sun.star.script.provider.LanguageScriptProvider",
     "com.sun.star.script.provider.ScriptProviderFor" + LANGUAGENAME,),)


log.debug("pythonscript finished intializing")
