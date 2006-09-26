#! /usr/bin/env python
#
# A post-commit hook for Subversion to send commit emails in the style
# of the OpenBSD CVS commit emails.
#
# USAGE:
#    post-commit.py [options] </path/to/repo> <revision>
#
# OPTIONS:
#
#    --mailto      Email address to mail commit message to.
#    --changelog   Filename to append commit message to.
#    --authors     A file that contains a map of usernames to full names
#                  and email addresses.  See authors.txt for an example.
#
# * One of --mailto or --changelog must be specified.
#
# Usage from hooks/post-commit:
#
# python /path/to/post-commit.py --mailto commits@domain.com --changelog /path/to/ChangeLog" \
#    "$REPOS" "$REV"
#

import sys
import os
import os.path
import commands
import getopt
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

SENDMAIL_PATH = "/usr/sbin/sendmail"

def sendmail(sendto, subject, buf, from_addr):
    """ Send the commit email. """
    sm = os.popen("%s %s" % (SENDMAIL_PATH, sendto), "w")
    if from_addr:
        sm.write("From: %s\n" % from_addr)
    sm.write("To: %s\n" % sendto)
    sm.write("Subject: SVN Commit: %s\n" % subject)
    sm.write("\n")
    sm.write(buf)
    sm.write("\n")
    sm.close()

def update_changelog(changelog, buf):
    """ Appends buf to the changelog file. """
    changeoutput = open(changelog, "a")
    changeoutput.write("===>\n")
    changeoutput.write(buf)
    changeoutput.write("\n")
    changeoutput.close()

def lookup_author(author_file, author):
    authors = open(author_file)
    while 1:
        line = authors.readline()
        if not line:
            break
        if line.startswith("#"):
            continue
        try:
            username, email = line.split("\t")
            if username == author:
                return email.strip()
        except:
            continue

    # Default, return the author as passed in.
    return author

def main(argv=None):
    if not argv:
        argv = sys.argv

    changelog = None
    mailto = None
    authors = None
    try:
        opts, args = getopt.getopt(argv[1:], "", ["mailto=", "changelog=", "authors="])
    except getopt.GetoptError:
        sys.exit(1)
    for o, a in opts:
        if o == "--mailto":
            mailto = a
        if o == "--changelog":
            changelog = a
        if o == "--authors":
            authors = a

    repo = args[0]
    rev = int(args[1])

    # We must have a --mailto or --changelog.
    if not (mailto or changelog):
        # Nothing to do!
        sys.stderr.write("Nothing to do!\n")
        sys.exit(1)

    # Get the author, date and log message.
    info = commands.getoutput("svnlook info %s" % repo)
    (author,
     date,
     loglen,
     log) = info.split("\n")

    if authors:
        try:
            author_full = lookup_author(authors, author)
        except:
            author_full = None

    # Get the list of files that have been modified, added and
    # deleted.
    changed = commands.getoutput("svnlook changed %s" % repo)
    modified = []
    added = []
    deleted = []
    other = []
    modules = []
    for i in changed.split("\n"):
        try:
            code, path = i.split()
        except:
            other.append(i)
        if code == "U":
            modified.append(path)
        elif code == "A":
            added.append(path)
        elif code == "D":
            deleted.append(path)
        else:
            other.append(path)

        if path.find("/") > -1:
            module = path.split("/")[0]
        else:
            module = path
        if module not in modules:
            modules.append(module)

    output = StringIO()

    output.write("Changes by: %s\n" % author.strip())
    output.write("Date:       %s\n" % date.strip())
    output.write("Revision:   %d\n" % rev)
    output.write("\n")

    if modified:
        output.write("Modified:\n")
        for f in modified:
            output.write("\t%s\n" % f)
        output.write("\n")

    if added:
        output.write("Added:\n")
        for f in added:
            output.write("\t%s\n" % f)
        output.write("\n")

    if deleted:
        output.write("Deleted:\n")
        for f in deleted:
            output.write("\t%s\n" % f)
        output.write("\n")

    if other:
        output.write("Other:\n")
        for f in deleted:
            output.write("\t%s\n" % f)
        output.write("\n")

    output.write("Log message:\n")
    output.write(log)
    output.write("\n")

    # Send the email.
    if mailto:
        sendmail(mailto, ", ".join(modules), output.getvalue(), author_full)

    # Update the changelog.
    if changelog:
        update_changelog(changelog, output.getvalue())

if __name__ == "__main__":
    sys.exit(main())
