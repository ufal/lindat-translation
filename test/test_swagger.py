import unittest
from swagger_tester import swagger_test
from swagger_parser import SwaggerParser


class TestTester(unittest.TestCase):

    def test_server(self):
        def monkeypatch_method(cls):
            """Add the decorated method to the given class; replace as needed.

            If the named method already exists on the given class, it will
            be replaced, and a reference to the old method appended to a list
            at cls._old_<name>. If the "_old_<name>" attribute already exists
            and is not a list, KeyError is raised.
            """

            def decorator(func):
                fname = func.__name__

                old_func = getattr(cls, fname, None)
                if old_func is not None:
                    # Add the old func to a list of old funcs.
                    old_ref = "_old_%s" % fname
                    old_funcs = getattr(cls, old_ref, None)
                    if old_funcs is None:
                        setattr(cls, old_ref, [])
                    elif not isinstance(old_funcs, list):
                        raise KeyError("%s.%s already exists." %
                                       (cls.__name__, old_ref))
                    getattr(cls, old_ref).append(old_func)

                setattr(cls, fname, staticmethod(func))
                return func

            return decorator

        @monkeypatch_method(SwaggerParser)
        def check_type(value, type_def):
            #print("Monkeypatched")
            #return SwaggerParser._old_check_type[0](value, type_def)
            if not SwaggerParser._old_check_type[0](value, type_def):
                print("monkey patched checked_type for `object` value={}; type_def={}"
                      .format(value, type_def))
                if type_def == 'object':
                    return isinstance(value, dict)
            else:
                return True

        # TODO should swagger.json be available at root?
        swagger_test(app_url='http://localhost:5000/api/v2')
