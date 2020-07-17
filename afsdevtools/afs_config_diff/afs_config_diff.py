#!/usr/bin/python
# Copyright (c) 2020, Sine Nomine Associates
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys
import re
import argparse

cache_vars_ignore = [
            "ac_cv_path_EGREP",
            "ac_cv_path_FGREP",
            "ac_cv_path_GREP",
            "ac_cv_path_PATH_CPP",
            "ac_cv_path_PATH_KRB5_CONFIG",
            "ac_cv_path_SED",
            "ac_cv_path_ac_pt_PKG_CONFIG",
            "ac_cv_path_install",
            "ac_cv_path_lt_DD" ,
            "lt_cv_path_LD",
            "lt_cv_path_NM",
            "lt_cv_path_mainfest_tool",
            ]
env_vars_ignore = [
            "BSD_KERNEL_PATH",
            "COMPILE_ET_PATH",
            "CONFIGTOOL_PATH",
            "DEST",
            "DOCBOOK_STYLESHEETS",
            "HELPER_SPLINT",
            "HELPER_SPLINTCFG",
            "LINUX_KERNEL_BUILD",
            "LINUX_KERNEL_PATH",
            "PATH_CPP",
            "PATH_KRB5_CONFIG",
            "PKG_CONFIG",
            "RXGEN_PATH",
            "TOP_INCDIR",
            "TOP_LIBDIR",
            "TOP_OBJDIR",
            "TOP_SRCDIR",
            ]
confdef_vars_ignore = [
            ]


class _Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class logfile:

    def __init__(self, cf):
        with open(cf) as self.configfile:
            self.find_str(r'^## Cache variables. ##$')

            self.cache_vars = {k:v for (k,v) in [self.parse_kv(_)
                for _ in self.match_strs(r'^[^# \t]\S+=',
                                         r'^## Output variables\. ##')] }
            self.env_vars = {k:v for (k,v) in [self.parse_kv(_)
                for _ in self.match_strs(r'^[^# \t]\S+=', 
                                         r'^## confdefs\.h\. ##')] }
            self.confdef_vars = {k:v for (k,v) in [self.parse_define(_)
                for _ in self.match_strs(r'^#\s*define\s+\S+',
                                         r'^configure: exit')] }    

    def find_str(self,s):
        pat = re.compile(s)
        for line in self.configfile:
            line = line.strip()
            if pat.match(line):
                return line
        raise EOFError

    def match_strs(self, matching, stopper):
        match_pat = re.compile(matching)
        stop_pat = re.compile(stopper)
        for line in self.configfile:
            line = line.strip()
            if stop_pat.match(line):
                return
            if match_pat.match(line):
                yield line
        raise EOFError

    def parse_kv(self, s):
        key, sep, val = s.partition('=')
        rv = (key.strip(), val.strip())
        return rv

    def parse_define(self, s):
        r = re.match(r'\s*#\s*define\s+(\S+)((\s+(\S+))+|\Z)', s)
        rv = (r.group(1).strip(), r.group(2).strip())
        return rv

class report:

    def __init__(self, header, delta):
        self.header = header
        self.delta = delta
    
    def print_hdr(self):
        print(self.header)
    
    def _dodetail(self, kv, section, sectionpad):
        if len(kv) == 0:
            print("    {0:{1}} None".format(section, sectionpad))
            return False
        else:
            print("    {0}".format(section))
            return True
    
    def print_kv(self, kv, section, sectionpad):
        if self._dodetail(kv, section, sectionpad):
            mlk = 0
            for (k, v) in kv:
                mlk = max(mlk, len(k))
            for (k, v) in kv:
                print("      {0:{1}} : {2}".format(k, mlk, v))

    def print_kvv(self, kvv, section, sectionpad):
        if self._dodetail(kvv, section, sectionpad):
            mlk = 0
            for (k, o, n) in kvv:
                mlk = max(mlk, len(k))
            for (k,o,n) in kvv:
                print("      {0:{1}} : {2}\n       {3:{4}}  {5}".
                      format(k, mlk, o, "=>", ">"+str(mlk), n))
    def print_report(self):
        self.print_hdr()
        self.print_kv(self.delta.added, "Added:", 8)
        self.print_kv(self.delta.removed, "Removed:", 8)
        self.print_kvv(self.delta.changed, "Changed:", 8)

class confdefreport(report):
    
    def print_kv(self, kv, section, sectionpad):
        if self._dodetail(kv, section, sectionpad):
            mlk = 0
            for (k, v) in kv:
                mlk = max(mlk, len(k))
            for (k, v) in kv:
                if str(v) != "1":
                    print("      {0:{1}} : {2}".format(k, mlk, v))
                else:
                    print("      {0:{1}}".format(k, mlk))

    def print_kvv(self, kvv, section, sectionpad):
        if self._dodetail(kvv, section, sectionpad):
            mlk = 0
            for (k, o, n) in kvv:
                mlk = max(mlk, len(k))
            for (k,o,n) in kvv:
                p = "      {0:{1}}".format(k, mlk)
                if str(o) != "1":
                    p += " : {0}".format(o)
                if str(n) != "1":
                    p += "\n       {0:{1}}  {2}".format("=>", ">"+str(mlk), n)

                print(p)

def gen_report(header, reporter, o, n, keysignore):
        """
            Returns
                .added: list of (key, val) that are in n but not in o
                .removed: list of (key, val) that are in o but non in n
                .changed: list of (key, oldval, newval) for matching keys with a changed value

        """
        o_keys = set(o.keys())
        n_keys = set(n.keys())

        added = [(_, n[_]) for _ in list(n_keys - o_keys)]
        removed = [(_, o[_]) for _ in list( o_keys - n_keys)]

        changed = []
        for k in o_keys & n_keys:
            if keysignore and k in keysignore:
                continue
            if o[k] != n[k]:
                changed.append( (k, o[k], n[k]) )
        delta = _Namespace(
            added=added, 
            removed=removed,
            changed=changed)
        reporter(header, delta).print_report()

def afs_config_diff(oldlog, newlog):

    try:
        oldlogs = logfile(oldlog)
    except Exception as e:
        print("Error processing old config '%s': %s" % (oldlog, e))
        exit(12)

    try:
        newlogs = logfile(newlog)
    except Exception as e:
        print("Error processing new config '%s': %s" % (newlog, e))
        exit(12)

    gen_report("Changes in autoconf settings",
               report, 
               oldlogs.cache_vars,
               newlogs.cache_vars,
               cache_vars_ignore)

    gen_report("Changes in ENV settings",
               report, 
               oldlogs.env_vars,
               newlogs.env_vars,
               env_vars_ignore)

    gen_report("Changes in confdefs",
               confdefreport,
               oldlogs.confdef_vars,
               newlogs.confdef_vars,
               confdef_vars_ignore)


def main():
    parser = argparse.ArgumentParser(description="Compare configure logs")
    parser.add_argument('old', help="old configuration log")
    parser.add_argument('new', help="new configuration log")

    args = parser.parse_args()

    afs_config_diff(args.old, args.new)
    
if __name__ == "__main__":
    main()
