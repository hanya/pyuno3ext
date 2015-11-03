/**************************************************************
 * 
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 * 
 *************************************************************/


#include "pyuno_impl.hxx"

#include <osl/thread.h>
#include <rtl/ustrbuf.hxx>
#include <rtl/strbuf.hxx>

using rtl::OUStringToOString;
using rtl::OUString;
using com::sun::star::uno::Sequence;
using com::sun::star::uno::Reference;
using com::sun::star::uno::XInterface;
using com::sun::star::uno::Any;
using com::sun::star::uno::Type;
using com::sun::star::uno::TypeClass;
using com::sun::star::uno::RuntimeException;
using com::sun::star::uno::XComponentContext;
using com::sun::star::lang::XMultiComponentFactory;
using com::sun::star::script::XTypeConverter;
using com::sun::star::script::XInvocation2;
using com::sun::star::reflection::XParameter;
using com::sun::star::reflection::XServiceConstructorDescription;

namespace pyuno
{
typedef struct
{
    Reference<XInvocation2> xInvocation;
    OUString methodName;
    ConversionMode mode;
} PyUNO_callable_Internals;

typedef struct
{
    PyObject_HEAD
    PyUNO_callable_Internals* members;
} PyUNO_callable;

void PyUNO_callable_del (PyObject* self)
{
    PyUNO_callable* me;
  
    me = (PyUNO_callable*) self;
    delete me->members;
    PyObject_Del (self);
  
    return;
}

PyObject* PyUNO_callable_call (PyObject* self, PyObject* args, PyObject*)
{
    PyUNO_callable* me;

    Sequence<short> aOutParamIndex;
    Sequence<Any> aOutParam;
    Sequence<Any> aParams;
    Sequence<Type> aParamTypes;
    Any any_params;
    Any out_params;
    Any ret_value;
    RuntimeCargo *cargo = 0;
    me = (PyUNO_callable*) self;
  
    PyRef ret;
    try
    {
        Runtime runtime;
        cargo = runtime.getImpl()->cargo;
        any_params = runtime.pyObject2Any (args, me->members->mode);
    
        if (any_params.getValueTypeClass () == com::sun::star::uno::TypeClass_SEQUENCE)
        {
            any_params >>= aParams;
        }
        else
        {
            aParams.realloc (1);
            aParams [0] <<= any_params;
        }

        {
            PyThreadDetach antiguard; //pyhton free zone
            
            // do some logging if desired ... 
            if( isLog( cargo, LogLevel::CALL ) )
            {
                logCall( cargo, "try     py->uno[0x", me->members->xInvocation.get(),
                         me->members->methodName, aParams );
            }

            // do the call
            ret_value = me->members->xInvocation->invoke (
                me->members->methodName, aParams, aOutParamIndex, aOutParam);

            // log the reply, if desired
            if( isLog( cargo, LogLevel::CALL ) )
            {
                logReply( cargo, "success py->uno[0x", me->members->xInvocation.get(),
                          me->members->methodName, ret_value, aOutParam);
            }
        }
        

        PyRef temp = runtime.any2PyObject (ret_value);
        if( aOutParam.getLength() )
        {
            PyRef return_list( PyTuple_New (1+aOutParam.getLength()), SAL_NO_ACQUIRE );
            PyTuple_SetItem (return_list.get(), 0, temp.getAcquired());

            // initialize with defaults in case of exceptions
            int i;
            for( i = 1 ; i < 1+aOutParam.getLength() ; i ++ )
            {
                Py_INCREF( Py_None );
                PyTuple_SetItem( return_list.get() , i , Py_None );
            }
            
            for( i = 0 ; i < aOutParam.getLength() ; i ++ )
            {
                PyRef ref = runtime.any2PyObject( aOutParam[i] );
                PyTuple_SetItem (return_list.get(), 1+i, ref.getAcquired());
            }
            ret = return_list;
        }
        else
        {
            ret = temp;
        }
    }
    catch( com::sun::star::reflection::InvocationTargetException & e )
    {
        
        if( isLog( cargo, LogLevel::CALL ) )
        {
            logException( cargo, "except  py->uno[0x", me->members->xInvocation.get() ,
                          me->members->methodName, e.TargetException.getValue(), e.TargetException.getValueTypeRef());
        }
        raisePyExceptionWithAny( e.TargetException );
    }
    catch( com::sun::star::script::CannotConvertException &e )
    {
        if( isLog( cargo, LogLevel::CALL ) )
        {
            logException( cargo, "error  py->uno[0x", me->members->xInvocation.get() ,
                          me->members->methodName, &e, getCppuType(&e).getTypeLibType());
        }
        raisePyExceptionWithAny( com::sun::star::uno::makeAny( e ) );
    }
    catch( com::sun::star::lang::IllegalArgumentException &e )
    {
        if( isLog( cargo, LogLevel::CALL ) )
        {
            logException( cargo, "error  py->uno[0x", me->members->xInvocation.get() ,
                          me->members->methodName, &e, getCppuType(&e).getTypeLibType());
        }
        raisePyExceptionWithAny( com::sun::star::uno::makeAny( e ) );
    }
    catch (::com::sun::star::uno::RuntimeException &e)
    {
        if( cargo && isLog( cargo, LogLevel::CALL ) )
        {
            logException( cargo, "error  py->uno[0x", me->members->xInvocation.get() ,
                          me->members->methodName, &e, getCppuType(&e).getTypeLibType());
        }
        raisePyExceptionWithAny( com::sun::star::uno::makeAny( e ) );
    }

    return ret.getAcquired();
}


static PyTypeObject PyUNO_callable_Type =
{
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    const_cast< char * >("PyUNO_callable"),
    sizeof (PyUNO_callable),
    0,
    (destructor) ::pyuno::PyUNO_callable_del,
    (printfunc) 0,
    (getattrfunc) 0,
    (setattrfunc) 0,
#if PY_MAJOR_VERSION >= 3
    0, 
#else
    (cmpfunc) 0,
#endif
    (reprfunc) 0,
    0,
    0,
    0,
    (hashfunc) 0,
    (ternaryfunc) ::pyuno::PyUNO_callable_call,
    (reprfunc) 0,
        (getattrofunc)0,
    (setattrofunc)0,
    NULL,
    0,
    NULL,
    (traverseproc)0,
    (inquiry)0,
    (richcmpfunc)0,
    0,
    (getiterfunc)0,
    (iternextfunc)0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (descrgetfunc)0,
    (descrsetfunc)0,
    0,
    (initproc)0,
    (allocfunc)0,
    (newfunc)0,
    (freefunc)0,
    (inquiry)0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (destructor)0
#if PY_VERSION_HEX >= 0x02060000
    , 0
#endif
};

PyRef PyUNO_callable_new (
    const Reference<XInvocation2> &my_inv,
    const OUString & methodName,
    enum ConversionMode mode )
{
    PyUNO_callable* self;
  
    self = PyObject_New (PyUNO_callable, &PyUNO_callable_Type);
    if (self == NULL)
        return NULL; //NULL == Error!

    self->members = new PyUNO_callable_Internals;
    self->members->xInvocation = my_inv;
    self->members->methodName = methodName;
    self->members->mode = mode;

    return PyRef( (PyObject*)self, SAL_NO_ACQUIRE );
}


typedef struct
{
    OUString serviceName;
    OUString constructorName;
    Reference< XServiceConstructorDescription > xConstructorDescription;
} PyUNO_service_constructor_internals;

typedef struct
{
    PyObject_HEAD
    PyUNO_service_constructor_internals * members;
} PyUNO_service_constructor;

void PyUNO_service_constructor_del(PyObject* self)
{
    PyUNO_service_constructor * me;
    
    me = (PyUNO_service_constructor *) self;
    delete me->members;
    PyObject_Del(self);
  
    return;
}

PyObject* PyUNO_service_constructor_call(PyObject* self, PyObject* args, PyObject*)
{
    PyUNO_service_constructor * me;
    
    me = (PyUNO_service_constructor *) self;
    try
    {
        Runtime runtime;
        const int nPassedLength = PyTuple_Size( args );
        Sequence< Any > aArguments;
        int nOutparam = 0;
        
        if ( me->members->xConstructorDescription.is() )
        {
            Sequence< Reference< XParameter > > aParameters( 
                        me->members->xConstructorDescription->getParameters() );
            if ( nPassedLength != aParameters.getLength() )
            {
                rtl::OStringBuffer buf;
                buf.append( OUStringToOString( me->members->constructorName, RTL_TEXTENCODING_ASCII_US ) )
                   .append( "() takes exactly " ).append( aParameters.getLength() )
                   .append( " arguments (" ).append( nPassedLength ).append( " given)" );
                PyErr_SetString( PyExc_TypeError, buf.getStr() );
                return 0;
            }
            
            aArguments.realloc( nPassedLength );
            const Reference< XParameter > * pParameters = aParameters.getConstArray();
            Any * pArguments = aArguments.getArray();
            Reference< XParameter > xParameter;
            for ( sal_Int32 n = 0; n < nPassedLength; ++n )
            {
                xParameter = pParameters[n];
                if ( xParameter.is() )
                {
                    if ( xParameter->isIn() )
                    {
                        Any a( runtime.pyObject2Any( PyTuple_GetItem( args, n ) ) );
                        const Type t( xParameter->getType()->getTypeClass(), xParameter->getType()->getName() );
                        if ( a.isExtractableTo( t ) )
                        {
                            pArguments[n] = a;
                        }
                        else
                        {
                            pArguments[n] = runtime.getImpl()->cargo->xTypeConverter->convertTo(a, t);
                        }
                    }
                    else if ( xParameter->isOut() )
                    {
                        ++nOutparam;
                    }
                }
            }
            Reference< XComponentContext > xContext = runtime.getImpl()->cargo->xContext;
            Reference< XMultiComponentFactory > xFactory = xContext->getServiceManager();
            Reference< XInterface > xInterface = xFactory->createInstanceWithArgumentsAndContext(
                                me->members->serviceName, aArguments, xContext );
            
            PyRef ret;
            if ( nOutparam > 0 )
            {
                PyRef pyRet = runtime.any2PyObject( makeAny( xInterface ) );
                PyRef reTuple( PyTuple_New( nOutparam + 1 ), SAL_NO_ACQUIRE );
                PyTuple_SetItem( reTuple.get(), 0, pyRet.getAcquired() );
                for ( sal_Int32 n = 1; n < nOutparam; ++n )
                {
                    Py_INCREF( Py_None );
                    PyTuple_SetItem( reTuple.get(), n, Py_None );
                }
                int nPos = 1;
                for ( sal_Int32 n = 0; n < nPassedLength; ++n )
                {
                    xParameter = pParameters[n];
                    if ( xParameter.is() )
                    {
                        if ( xParameter->isOut() )
                        {
                            PyRef ref = runtime.any2PyObject( pArguments[n] );
                            PyTuple_SetItem( reTuple.get(), nPos, ref.getAcquired() );
                            ++nPos;
                        }
                    }
                }
                ret = reTuple;
            }
            else
            {
                ret = runtime.any2PyObject( makeAny( xInterface ) );
            }
            return ret.getAcquired();
        }
        else
        {
            aArguments.realloc( nPassedLength );
            Any * pArguments = aArguments.getArray();
            for ( sal_Int32 n = 0; n < nPassedLength; ++n )
            {
                pArguments[n] = runtime.pyObject2Any( PyTuple_GetItem( args, n ) );
            }
        }
        Reference< XComponentContext > xContext = runtime.getImpl()->cargo->xContext;
        Reference< XMultiComponentFactory > xFactory = xContext->getServiceManager();
        Reference< XInterface > xInterface = xFactory->createInstanceWithArgumentsAndContext(
                            me->members->serviceName, aArguments, xContext );
        
        PyRef ret( runtime.any2PyObject( makeAny( xInterface ) ) );
        return ret.getAcquired();
    }
    catch( com::sun::star::lang::IllegalArgumentException &e )
    {
        raisePyExceptionWithAny( makeAny(e) );
    }
    catch( com::sun::star::script::CannotConvertException &e )
    {
        raisePyExceptionWithAny( makeAny(e) );
    }
    catch ( RuntimeException & e )
    {
        raisePyExceptionWithAny( makeAny(e) );
    }
    catch ( com::sun::star::uno::Exception & e )
    {
        raisePyExceptionWithAny( makeAny( e ) );
    }
    return 0;
}

static PyTypeObject PyUNO_service_constructor_Type =
{
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    const_cast< char * >("PyUNO_service_constructor"),
    sizeof (PyUNO_service_constructor),
    0,
    (destructor) ::pyuno::PyUNO_service_constructor_del,
    (printfunc) 0,
    (getattrfunc) 0,
    (setattrfunc) 0,
#if PY_MAJOR_VERSION >= 3
    0, 
#else
    (cmpfunc) 0,
#endif
    (reprfunc) 0,
    0,
    0,
    0,
    (hashfunc) 0,
    (ternaryfunc) ::pyuno::PyUNO_service_constructor_call,
    (reprfunc) 0,
    (getattrofunc)0,
    (setattrofunc)0,
    NULL,
    0,
    NULL,
    (traverseproc)0,
    (inquiry)0,
    (richcmpfunc)0,
    0,
    (getiterfunc)0,
    (iternextfunc)0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (descrgetfunc)0,
    (descrsetfunc)0,
    0,
    (initproc)0,
    (allocfunc)0,
    (newfunc)0,
    (freefunc)0,
    (inquiry)0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (destructor)0
#if PY_VERSION_HEX >= 0x02060000
    , 0
#endif
};

PyRef PyUNO_service_constructor_new(
    const OUString & serviceName, 
    const OUString & constructorName, 
    const Reference< XServiceConstructorDescription > & xDesc )
{
    PyUNO_service_constructor * self;
    
    self = PyObject_New(PyUNO_service_constructor, &PyUNO_service_constructor_Type);
    if (self == NULL)
        return NULL;

    self->members = new PyUNO_service_constructor_internals;
    self->members->serviceName = serviceName;
    self->members->constructorName = constructorName;
    self->members->xConstructorDescription = xDesc;

    return PyRef( (PyObject*)self, SAL_NO_ACQUIRE );
}

}
