
# Update to match with Python
PY_MAJOR=3
PY_MINOR=5
PY_BUGFX=0
PY_VERSION=$(PY_MAJOR).$(PY_MINOR).$(PY_BUGFX)
PY_SHORT_VERSION=$(PY_MAJOR).$(PY_MINOR)

OPENSSL_VERSION=0.9.8zg


# Loader definitions
LOADER_EXT_NAME=Python$(PY_SHORT_VERSION)Loader
LOADER_EXT_VERSION=0.1.0
LOADER_EXT_STATE=

# Scripting definitions
SCRIPTING_EXT_NAME=PythonScript
SCRIPTING_EXT_VERSION=0.1.0
SCRIPTING_EXT_STATE=

####

PRJ=$(OO_SDK_HOME)
SETTINGS=$(PRJ)/settings

include $(SETTINGS)/settings.mk
include $(SETTINGS)/std.mk
include $(SETTINGS)/dk.mk
include $(SETTINGS)/platform.mk


LOADER_EXT_PKG_NAME=$(LOADER_EXT_NAME)-$(LOADER_EXT_VERSION)$(LOADER_EXT_STATE)-$(subst _,-,$(EXTENSION_PLATFORM)).$(UNOOXT_EXT)
SCRIPTING_EXT_PKG_NAME=$(SCRIPTING_EXT_NAME)-$(SCRIPTING_EXT_VERSION)$(SCRIPTING_EXT_STATE).$(UNOOXT_EXT)


ifeq "$(PY_MAJOR)" "3"
	LIB_SUFFIX=m
else
	LIB_SUFFIX=
endif


ifeq "$(OS)" "WIN"
	# Not yet supported
	DOWN_LOADER=
	TAR_CMD=tar xvf
	PATCH_CMD=patch
	
	CONFIG_FILE_SUFFIX=.ini
	ORIGIN_NAME=%%origin%%
	CC_FLAGS+= /O2
	LINK_OUT_FLAG=/OUT: 
	# ToDo
	PYTHON_LIB=
	LINK_LIB_SWITCH=/LIBPATH:
	MODULE_PYUNO_LINK=
	PYUNO_LIB=pyuno.lib
else
	DOWN_LOADER=wget
	TAR_CMD=tar xvf
	PATCH_CMD=patch
	
	CONFIG_FILE_SUFFIX=rc
	ORIGIN_NAME=%origin%
	CC_FLAGS=-c -O2 -fpic
	LINK_OUT_FLAG=-o 
	PYTHON_LIB=-lpython$(PY_MAJOR).$(PY_MINOR)$(LIB_SUFFIX)
	PYUNO_LIB=-lpyuno
	LINK_LIB_SWITCH=-L
	MODULE_PYUNO_LINK=-ldl
	DEFAULT_LD_LIBRARY_PATH=/usr/local/lib
	
	COMP_LINK_FLAGS=$(LIBRARY_LINK_FLAGS) 
	COMP_LINK_FLAGS+= -Wl,--version-script,$(SETTINGS)/component.uno.map 
	
	ifeq "$(PROCTYPE)" "x86_64"
		OPENSSL_PLATFORM=linux-generic64
	endif
	ifeq "$(PROCTYPE)" "i386"
		OPENSSL_PLATFORM=linux-generic32
	endif
	OPENSSL_SHARED_OPTION=shared
endif

MODULE_LINK_FLAGS=$(LIBRARY_LINK_FLAGS)
PYTHON_EXEC_NAME=python$(EXE_EXT)


BUILD_DIR=./build$(PY_SHORT_VERSION)
LOADER_BUILD_DIR=$(BUILD_DIR)/loader
LOADER_BUILD_LIB_DIR=$(LOADER_BUILD_DIR)/lib
SCRIPTING_BUILD_DIR=$(BUILD_DIR)/scripting


README_NAME=README.md
LICENSE_NAME=LICENSE
CHANGES_NAME=CHANGES.md
PY_FILES=*.py
COMPONENTS_FILES=*.components
DESCRIPTION_XML_NAME=description.xml
META_INF_MANIFEST_NAME=$(subst /,$(PS),META-INF/manifest.xml)


PYUNO_DIR=./pyuno
PYUNO_MODULE_NAME=pyuno.$(SHAREDLIB_EXT)
LIB_PYUNO_NAME=$(SHAREDLIB_PRE)pyuno.$(SHAREDLIB_EXT)

MODULE_DIR=./pyuno/source/module
MODULE_CXX_FILES=pyuno.cxx pyuno_adapter.cxx pyuno_callable.cxx pyuno_except.cxx \
                 pyuno_gc.cxx pyuno_module.cxx pyuno_runtime.cxx pyuno_type.cxx pyuno_util.cxx
MODULE_C_FILES=pyuno_dlopenwrapper.c
MODULE_OUT_SLO=$(LOADER_BUILD_DIR)/slo
LIB_PYUNO_OBJ_FILES=$(patsubst %.cxx,$(MODULE_OUT_SLO)/%.$(OBJ_EXT),$(MODULE_CXX_FILES))
MODULE_PYUNO_OBJ_FJILES=$(patsubst %.c,$(MODULE_OUT_SLO)/%.$(OBJ_EXT),$(MODULE_C_FILES))

LIB_PYUNO=$(LOADER_BUILD_LIB_DIR)/$(LIB_PYUNO_NAME)
MODULE_PYUNO=$(LOADER_BUILD_LIB_DIR)/$(PYUNO_MODULE_NAME)

LOADER_DIR=./pyuno/source/loader
LOADER_CXX_FILES=pyuno_loader.cxx
LOADER_OBJ_FILES=$(patsubst %.cxx,$(MODULE_OUT_SLO)/%.$(OBJ_EXT),$(LOADER_CXX_FILES))
LOADER_PY_FILE=$(LOADER_BUILD_LIB_DIR)/pythonloader.py
MODULE_UNO_PY_NAME=uno.py
MODULE_HELPER_PY_NAME=unohelper.py

MODULE_UNO_PY_FILE=$(LOADER_BUILD_LIB_DIR)/$(MODULE_UNO_PY_NAME)
MODULE_HELPER_FILE=$(LOADER_BUILD_LIB_DIR)/$(MODULE_HELPER_PY_NAME)

LOADER_COMP_NAME=pythonloader.uno.$(SHAREDLIB_EXT)
LOADER_CONFIG_NAME=pythonloader.uno$(CONFIG_FILE_SUFFIX)

LOADER_MANIFEST=$(LOADER_BUILD_DIR)/$(META_INF_MANIFEST_NAME)
LOADER_REGISTRATION_COMPONENTS=$(LOADER_BUILD_LIB_DIR)/loader.components
LOADER_BOOTSTRAP_CONFIG=$(LOADER_BUILD_LIB_DIR)/pythonloader.uno$(CONFIG_FILE_SUFFIX)
LOADER_COMP=$(LOADER_BUILD_LIB_DIR)/$(LOADER_COMP_NAME)
LOADER_DESCRIPTION_XML=$(PYUNO_DIR)/$(DESCRIPTION_XML_NAME)

LOADER_EXT_PKG=$(LOADER_EXT_PKG_NAME)

# ToDo not yet supported
ZIPCORE_DIR=./zipcore

# SCRIPTING
SCRIPTING_DIR=./scripting
SCRIPTING_PY_FILE=$(SCRIPTING_DIR)/source/pyprov/pythonscript.py
SCRIPTING_REGISTRATION_COMPONENTS=$(SCRIPTING_DIR)/pythonscript.components
SCRIPTING_DESCRIPTION_XML=$(SCRIPTING_DIR)/$(DESCRIPTION_XML_NAME)
SCRIPTING_MAILMERGE_PY_FILE=$(SCRIPTING_DIR)/source/pyprov/mailmerge.py

SCRIPTING_EXT_PKG=$(SCRIPTING_EXT_PKG_NAME)
SCRIPTING_MANIFEST=./scripting/manifest.xml
SCRIPTING_PY=$(SCRIPTING_BUILD_DIR)/pythonscript.py
SCRIPTING_MAILMERGE_PY=$(SCRIPTING_BUILD_DIR)/mailmerge.py

PYTHON_INC=$(LOADER_BUILD_DIR)/include/python$(PY_MAJOR).$(PY_MINOR)$(LIB_SUFFIX)
PYUNO_INC=$(PYUNO_DIR)/inc
IDL_INC=./inc

MODULE_CC_INCLUDES=-I. -I$(IDL_INC) -I$(PRJ)/include -I$(PRJ)/include/stl -I$(PYUNO_INC) -I$(PYTHON_INC)
LOADER_CC_INCLUDES=-I. -I$(IDL_INC) -I$(PRJ)/include -I$(PYUNO_INC) -I$(PYTHON_INC)

MODULE_LINK_LIBS=-L$(OFFICE_PROGRAM_PATH) -L$(PRJ)$(PS)lib

PYTHON_LINK_LIB=$(LINK_LIB_SWITCH)$(LOADER_BUILD_LIB_DIR)
LOADER_LINK_LIB=$(LINK_LIB_SWITCH)$(LOADER_BUILD_LIB_DIR)
LOADER_COMP_ADDITIONAL_LIBS=-Wl,--as-needed -ldl -lpthread -lm -Wl,--no-as-needed -Wl,-Bdynamic


OPENSSL_NAME=openssl-$(OPENSSL_VERSION)
OPENSSL_ARCHIVE_NAME=$(OPENSSL_NAME).tar.gz
PYTHON_NAME=Python-$(PY_VERSION)
PYTHON_ARCHIVE_NAME=$(PYTHON_NAME).tgz

OPENSSL_DOWNLOAD_PATH=https://www.openssl.org/source/$(OPENSSL_ARCHIVE_NAME)
PYTHON_DOWNLOAD_PATH=https://www.python.org/ftp/python/$(PY_VERSION)/$(PYTHON_ARCHIVE_NAME)

PYTHON_PATCH_FLAG=$(PYTHON_NAME)/setup_patch.flag
PYTHON_SETUP_PATCH=setup.$(PY_SHORT_VERSION).patch

BUILD_PYTHON_LIB:=$(LOADER_BUILD_LIB_DIR)/python$(PY_SHORT_VERSION)

IDL_INC_FLAG=$(IDL_INC)$(PS)flag

PYTHON_EXE_NAME=python$(PY_SHORT_VERSION)$(EXE_EXT)
PYTHON_EXE_LINK_NAME=python$(PY_MAJOR)$(EXE_EXT)


.PHONY: ALL
ALL : $(IDL_INC_FLAG) Loader Scripting

Loader : $(LOADER_EXT_PKG) 

Scripting : $(SCRIPTING_EXT_PKG)


$(IDL_INC_FLAG) : 
	$(CPPUMAKER) -Gc -BUCR -O$(IDL_INC) $(OFFICE_TYPES)
	@echo flag >> $(IDL_INC_FLAG)


$(OPENSSL_ARCHIVE_NAME) : 
	$(DOWN_LOADER) $(OPENSSL_DOWNLOAD_PATH)

$(OPENSSL_NAME) : $(OPENSSL_ARCHIVE_NAME)
	$(TAR_CMD) $(OPENSSL_ARCHIVE_NAME)
	cd $(OPENSSL_NAME) && ./Configure $(OPENSSL_PLATFORM) $(OPENSSL_SHARED_OPTION) && make
	$(DEL) $(OPENSSL_NAME)/$(SHAREDLIB_PRE)ssl.$(SHAREDLIB_EXT)
	$(DEL) $(OPENSSL_NAME)/$(SHAREDLIB_PRE)crypto.$(SHAREDLIB_EXT)

$(OPENSSL_NAME)/libssl.a : $(OPENSSL_NAME)


$(PYTHON_ARCHIVE_NAME) : 
	$(DOWN_LOADER) $(PYTHON_DOWNLOAD_PATH)

$(PYTHON_NAME) : $(PYTHON_ARCHIVE_NAME)
	$(TAR_CMD) $(PYTHON_ARCHIVE_NAME)
	cd $(PYTHON_NAME) && $(PATCH_CMD) -p0 < ../$(PYTHON_SETUP_PATCH)
	@echo flag >> $(PYTHON_SETUP_PATCH)
	export LD_LIBRARY_PATH=$(DEFAULT_LD_LIBRARY_PATH) && cd $(PYTHON_NAME) && ./configure --enable-shared --prefix=$(CURDIR)/build${PY_SHORT_VERSION}/loader && make


$(PYTHON_NAME)/$(PYTHON_EXEC_NAME) : $(OPENSSL_NAME)/libssl.a $(PYTHON_NAME)


$(BUILD_PYTHON_LIB) : $(PYTHON_NAME)/$(PYTHON_EXEC_NAME)
	export LD_LIBRARY_PATH=$(DEFAULT_LD_LIBRARY_PATH) && cd $(PYTHON_NAME) && make install


# ToDo add option to avoid packing .pyc files

# LOADER

$(LOADER_BUILD_DIR)/$(README_NAME) : $(README_NAME)
	$(COPY) $(README_NAME) $(LOADER_BUILD_DIR)

$(LOADER_BUILD_DIR)/$(LICENSE_NAME) : $(LICENSE_NAME)
	$(COPY) $(LICENSE_NAME) $(LOADER_BUILD_DIR)

$(LOADER_BUILD_DIR)/$(CHANGES_NAME) : $(CHANGES_NAME)
	$(COPY) $(CHANGES_NAME) $(LOADER_BUILD_DIR)

$(LOADER_BUILD_DIR)/$(DESCRIPTION_XML_NAME) : $(PYUNO_DIR)/description$(PY_MAJOR).xml
	$(COPY) $(PYUNO_DIR)/description$(PY_MAJOR).xml $(LOADER_BUILD_DIR)/$(DESCRIPTION_XML_NAME)


$(LOADER_EXT_PKG) : $(BUILD_PYTHON_LIB) $(LOADER_BUILD_LIB_DIR) $(LOADER_MANIFEST) $(LOADER_REGISTRATION_COMPONENTS) \
		$(LOADER_BOOTSTRAP_CONFIG) $(REGISTERFLAG) $(MODULE_OUT_SLO)  $(LOADER_COMP) $(MODULE_PYUNO) \
		$(LIB_PYUNO) $(MODULE_UNO_PY_FILE) $(MODULE_HELPER_FILE) $(LOADER_PY_FILE) \
		$(LOADER_BUILD_DIR)/$(README_NAME) $(LOADER_BUILD_DIR)/$(LICENSE_NAME) \
		$(LOADER_BUILD_DIR)/$(CHANGES_NAME) $(LOADER_BUILD_DIR)/$(DESCRIPTION_XML_NAME)
	cd $(LOADER_BUILD_DIR) && $(SDK_ZIP) -9 -r -o $(subst /,$(PS),../$(LOADER_EXT_PKG)) \
		$(META_INF_MANIFEST_NAME) $(README_NAME) $(LICENSE_NAME) $(CHANGES_NAME) $(DESCRIPTION_XML_NAME) \
		./lib/*.components ./lib/pythonloader.uno$(CONFIG_FILE_SUFFIX) \
		./include/*.* ./lib/*.py ./lib/*.$(SHAREDLIB_EXT) ./lib/*.$(SHAREDLIB_EXT).1.0 \
		./lib/python$(PY_SHORT_VERSION) ./bin/$(PYTHON_EXE_NAME) ./bin/$(PYTHON_EXE_LINK_NAME)

$(LIB_PYUNO) : $(REGISTERFLAG) $(LIB_PYUNO_OBJ_FILES)
	$(LINK) $(LINK_OUT_FLAG)$(LIB_PYUNO) $(MODULE_LINK_FLAGS) $(LIB_PYUNO_OBJ_FILES) $(MODULE_LINK_LIBS) $(PYTHON_LINK_LIB) $(SALLIB) $(SALDYLIB) $(SALHELPERLIB) $(CPPULIB) $(CPPUHELPERLIB) $(STC++LIB) $(CPPUHELPERDYLIB) $(CPPUDYLIB) $(ADDITIONAL_LIBS) $(PYTHON_LIB)

$(MODULE_PYUNO) : $(REGISTERFLAG) $(MODULE_PYUNO_OBJ_FJILES) $(LIB_PYUNO)
	$(LINK) $(LINK_OUT_FLAG)$(MODULE_PYUNO) $(MODULE_LINK_FLAGS) $(MODULE_PYUNO_OBJ_FJILES) $(MODULE_PYUNO_LINK) $(ADDITIONAL_LIBS)

$(LOADER_COMP) : $(REGISTERFLAG)  $(LOADER_OBJ_FILES) $(LIB_PYUNO) $(REGISTERFLAG)
	$(LINK) $(LINK_OUT_FLAG)$(LOADER_COMP) $(COMP_LINK_FLAGS) $(LOADER_OBJ_FILES) $(MODULE_LINK_LIBS) $(LOADER_LINK_LIB) $(PYTHON_LINK_LIB) $(SALLIB) $(SALDYLIB) $(SALHELPERLIB) $(CPPULIB) $(CPPUHELPERLIB) $(STC++LIB) $(CPPUHELPERDYLIB) $(CPPUDYLIB) $(PYUNO_LIB) $(PYTHON_LIB) $(LOADER_COMP_ADDITIONAL_LIBS)

$(MODULE_OUT_SLO)/%.$(OBJ_EXT) : $(REGISTERFLAG) $(MODULE_DIR)/%.cxx $(REGISTERFLAG)
	@-$(MKDIR) $(subst /,$(PS),$(@D))
	$(CC) $(CC_OUTPUT_SWITCH)$(subst /,$(PS),$@) $(CC_FLAGS) $< $(MODULE_CC_INCLUDES) $(CC_DEFINES) $(VERSION_DEF) 

$(MODULE_OUT_SLO)/%.$(OBJ_EXT) : $(MODULE_DIR)/%.c
	$(CC) $(CC_OUTPUT_SWITCH)$(subst /,$(PS),$@) $(CC_FLAGS) $< $(MODULE_CC_INCLUDES) $(CC_DEFINES) $(VERSION_DEF) 

$(MODULE_OUT_SLO)/%.$(OBJ_EXT) : $(REGISTERFLAG) $(LOADER_DIR)/%.cxx $(REGISTERFLAG)
	@-$(MKDIR) $(subst /,$(PS),$(@D))
	$(CC) $(CC_OUTPUT_SWITCH)$(subst /,$(PS),$@) $(CC_FLAGS) $< $(LOADER_CC_INCLUDES) $(CC_DEFINES) $(VERSION_DEF) 

$(LOADER_PY_FILE) : 
	$(COPY) $(LOADER_DIR)/pythonloader.py $(LOADER_BUILD_LIB_DIR)


$(MODULE_OUT_SLO) :
	$(MKDIR) $(subst /,$(PS),$@)

$(LOADER_BUILD_LIB_DIR) : 
	$(MKDIR) $(subst /,$(PS),$@)

$(MODULE_UNO_PY_FILE) : 
	$(COPY) $(MODULE_DIR)/$(MODULE_UNO_PY_NAME) $(LOADER_BUILD_LIB_DIR)

$(MODULE_HELPER_FILE) :
	$(COPY) $(MODULE_DIR)/$(MODULE_HELPER_PY_NAME) $(LOADER_BUILD_LIB_DIR)

$(LOADER_MANIFEST) : 
	@-$(MKDIR) $(subst /,$(PS),$(@D))
	@echo $(OSEP)?xml version="$(QM)1.0$(QM)" encoding="$(QM)UTF-8$(QM)"?$(CSEP) > $@
	@echo $(OSEP)manifest:manifest$(CSEP) >> $@
	@echo $(OSEP)manifest:file-entry manifest:full-path="$(QM)lib/loader.components$(QM)"  >> $@
	@echo manifest:media-type="$(QM)application/vnd.sun.star.uno-components;platform=$(UNOPKG_PLATFORM)$(QM)"/$(CSEP)  >> $@
	@echo $(OSEP)/manifest:manifest$(CSEP) >> $@

$(LOADER_REGISTRATION_COMPONENTS) : 
	@echo $(OSEP)?xml version="$(QM)1.0$(QM)" encoding="$(QM)UTF-8$(QM)"?$(CSEP) > $@
	@echo $(OSEP)components xmlns="$(QM)http://openoffice.org/2010/uno-components$(QM)"$(CSEP) >> $@
	@echo $(OSEP)component loader="$(QM)com.sun.star.loader.SharedLibrary$(QM)" uri="$(QM)$(LOADER_COMP_NAME)$(QM)"$(CSEP) >> $@
	@echo $(OSEP)implementation name="$(QM)org.openoffice.comp.pyuno.Loader$(QM)"$(CSEP) >> $@
	@echo $(OSEP)service name="$(QM)com.sun.star.loader.Python$(QM)"/$(CSEP) >> $@
	@echo $(OSEP)/implementation$(CSEP) >> $@
	@echo $(OSEP)/component$(CSEP) >> $@
	@echo $(OSEP)/components$(CSEP) >> $@

$(LOADER_BOOTSTRAP_CONFIG) : 
	@echo [Bootstrap] > $@
	@echo PYUNO_LOADER_PYTHONHOME=\$$ORIGIN/../ >> $@
	@echo PYUNO_LOADER_PYTHONPATH=\$$ORIGIN/python$(PY_SHORT_VERSION) \$$ORIGIN/python$(PY_SHORT_VERSION)/lib-dynload \$$ORIGIN >> $@


# SCRIPTING

$(SCRIPTING_BUILD_DIR) : 
	$(MKDIR) $(subst /,$(PS),$@)

$(SCRIPTING_PY) : $(SCRIPTING_PY_FILE)
	$(COPY) $(SCRIPTING_PY_FILE) $(SCRIPTING_BUILD_DIR)

$(SCRIPTING_MAILMERGE_PY) : $(SCRIPTING_MAILMERGE_PY_FILE)
	$(COPY) $(SCRIPTING_MAILMERGE_PY_FILE) $(SCRIPTING_BUILD_DIR)

$(SCRIPTING_BUILD_DIR)/$(README_NAME) : $(README_NAME)
	$(COPY) $(README_NAME) $(subst /,$(PS),$(SCRIPTING_BUILD_DIR))

$(SCRIPTING_BUILD_DIR)/$(LICENSE_NAME) : $(LICENSE_NAME)
	$(COPY) $(LICENSE_NAME) $(subst /,$(PS),$(SCRIPTING_BUILD_DIR))

$(SCRIPTING_BUILD_DIR)/$(CHANGES_NAME) : $(CHANGES_NAME)
	$(COPY) $(CHANGES_NAME) $(subst /,$(PS),$(SCRIPTING_BUILD_DIR))

$(SCRIPTING_BUILD_DIR)/pythonscript.components : $(SCRIPTING_REGISTRATION_COMPONENTS)
	$(COPY) $(SCRIPTING_REGISTRATION_COMPONENTS) $(SCRIPTING_BUILD_DIR)

$(SCRIPTING_BUILD_DIR)/description.xml : $(SCRIPTING_DESCRIPTION_XML)
	$(COPY) $(SCRIPTING_DESCRIPTION_XML) $(SCRIPTING_BUILD_DIR)

$(SCRIPTING_BUILD_DIR)/META-INF/manifest.xml : $(SCRIPTING_MANIFEST)
	@-$(MKDIR) $(subst /,$(PS),$(SCRIPTING_BUILD_DIR)/META-INF)
	$(COPY) $(SCRIPTING_MANIFEST) $(subst /,$(PS),$(SCRIPTING_BUILD_DIR)/META-INF)

$(SCRIPTING_EXT_PKG) : $(SCRIPTING_BUILD_DIR) $(SCRIPTING_PY) $(SCRIPTING_MAILMERGE_PY) \
		$(SCRIPTING_BUILD_DIR)/$(README_NAME) $(SCRIPTING_BUILD_DIR)/$(LICENSE_NAME) \
		$(SCRIPTING_BUILD_DIR)/$(CHANGES_NAME) \
		$(SCRIPTING_BUILD_DIR)/pythonscript.components $(SCRIPTING_BUILD_DIR)/description.xml \
		$(SCRIPTING_BUILD_DIR)/META-INF/manifest.xml
	cd $(SCRIPTING_BUILD_DIR) && $(SDK_ZIP) -9 -o $(subst /,$(PS),../$(SCRIPTING_EXT_PKG)) \
		$(META_INF_MANIFEST_NAME) $(README_NAME) $(LICENSE_NAME) $(CHANGES_NAME) $(DESCRIPTION_XML_NAME) \
		$(COMPONENTS_FILES) $(PY_FILES)

clean : 
	@- $(DELRECURSIVE) $(BUILD_DIR)
