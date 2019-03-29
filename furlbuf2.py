# -*- coding: utf-8 -*-
#
# fUrlbuf and its versions are Copyright (c) 2019 by pX <@havok.org>
#
# original code Copyright (c) 2011-2014 by Jani Kesänen <jani.kesanen@gmail.com> until i haxed it under GPL3
#
# License: GPL3 - <http://www.gnu.org/licenses/>.
#
# fUrlbuf - a neat url logger (Fork of Urlbuf.py by pX @ EFNet)
#
# Collects received URLs from public and private messages into a single
# buffer. This buffer is especially handy if you spend lot's of time afk
# and you don't want to miss any of the cat pictures/videos that were pasted
# while you were doing something meaningful.
#
# History:
# 03.28.2019:
#   [v 1.1]: re-wrote is_url_listed to use hdata instead of infolist, it also works now.
#         +: skip_duplicates_num will check last XX lines in furlbuf_buffer for dupes
#         +: tinyurl now handling exceptions properly
#         +: added color function , cleaned up code a little
# 03.25.2019:
#   [v 1.0]: Don't print tinyurl in current buffer if a tinyurl is in message
# 03.21.2019:
#   [v 1.0]: included snippets from John Anderson's shortenurl.py.
#          : both scripts had a lot of similarities, combining them looks
#          : nice in fUrlbuffer.
#          : found a bug in processing skip_duplicates, disabled it for now
# 03.19.2019:
#   [v 0.8]: look and feel updates, customize most output now
#         +: check for old settings and import to new settings
#         +: added backlog when buffer is reopened
#         +: created some functions to clean up the look a little
#         +: fixed a bug to account for mixed settings
#         +: settings renamed
#         -: removed 'import_ok' and using 'quit()' instead if import weechat fails.
# 03.18.2019:
#   [v 0.7]: (found a bug in ACTION's.  Jani was ouputting 'prefix', but in the case of
#          : an ACTION the prefix is whatever 'weechat.look.prefix_action' is set to.
#          : Tags of interest will always include 'nick_<nick>', using this instead of prefix.)
# 03.17.2019:
#   [v 0.6]: allow coloring of own nick, variables for modular output, output formatting
#         +: moved buffer creation into a function
#         +: if buffer doesn't exist, create it
# 03.16.2019:
#	[v 0.5]: per Big Dave's request, added self url logging and config option.  HI BIG DAVE!
#         +: added unread marker
# 09.26.2019: px@havok.org - forked to fUrlbuf v0.1
#	[v 0.1]: forked urlbuf.py and modified to display a cleaner/easier to read output.
#
###################################################
# 2014-09-17, Jani Kesänen <jani.kesanen@gmail.com>
#   version 0.2: - added descriptions to settings.
# 2011-06-07, Jani Kesänen <jani.kesanen@gmail.com>
#   version 0.1: - initial release.
###################################################

try:
    import weechat as w
except ImportError:
    print 'This script must be run under WeeChat.'
    quit()

import re
from urllib import urlencode
import urllib2

SCRIPT_NAME    = 'fUrlbuf'
SCRIPT_AUTHOR  = 'pX @ EFNet'
SCRIPT_VERSION = '1.1'
SCRIPT_LICENSE = 'GPL3 - http://www.gnu.org/licenses/'
SCRIPT_DESC    = 'fUrlbuf - a neat url logger'

SETTINGS = {
    'output_left'                : ("[", "character(s) to left of nick"), ## @pX - 03.19.2019
    'output_left_color'          : ("gray", "color of character(s) left of nick"), ## @pX - 03.19.2019
    'output_right'               : ("] ", "character(s) to right of nick/buffer name"), ## @pX - 03.19.2019
    'output_right_color'         : ("gray", "color of character(s) right of nick"), ## @pX - 03.19.2019
    'output_sep'                 : (" / ", "<nick> / buffer separator(s)"), ## @pX - 03.19.2019
    'output_sep_color'           : ("gray", "color of nick / buffer separator(s)"), ## @pX - 03.19.2019
    'show_active_buffer'         : ("on", "catch urls from active buffer"),
    'show_backlog'               : ("on", "show backlog on buffer open ** change requires buffer close **"), ## @pX -03.19.2019
    'show_buffer_short'          : ("on", "show buffers short name"), ## changed from buffer_number. short_name is better imo -@pX
    'show_buffer_short_color'    : ("242", "color of buffer name"), ## dark gray - option to color buffer name -@pX
    'show_nicks'                 : ("on", "show nick of url poster"), ## forcing on .. why would you want it otherwise? -@pX
    'show_nicks_color'           : ("gray", "nick color of url poster"), ## option to color nick -@pX
    'show_private'               : ("on", "catch urls in private messages"),
    'show_private_color'         : ("red", "color for \'priv\' tag from private messages"), ## @pX - 03.19.2019
    'show_self'                  : ("on", "catch your own urls"), ## @pX 03.16.2019
    'show_self_color'            : ("white", "your own nick color"), ## @pX - 03.17.2019
    'show_unread'                : ("on", "show unread marker  ** change requires buffer close **"), ## @pX - 03.19.2019
    'skip_buffers'               : (" ", "comma separated list of buffer short names to skip (ex: hacker,privatechats)"),
    'skip_duplicates'            : ("off", "skip duplicate urls (will skip even if different nick)"), ## new default, i want to see all -@pX  03.17.2019
    'skip_duplicates_num'        : ("100", "check last XX messages for duplicates"), ## default, check last 100 lines for messages -@pX 03.28.2019
    # tinyurl settings -@pX 03.21.2019
    'url_shorten'                : ("on", "automatically shorten outgoing and incoming urls"),
    "url_color_tiny"             : ("lightgreen", "color of tinyurl"),
    "url_length"                 : ("30", "only process urls longer than"),
    "url_short_own"              : ("on", "shorten your outgoing urls"),
    "url_ignore"				 : ("http://is.gd,http://tinyurl.com,http://bit.ly", "don't shorten urls containing"),
}


octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\.%s){3}' % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
urlRe = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr), re.I)

TINYURL = 'http://tinyurl.com/api-create.php?%s'
furlbuf_buffer = None
global r
rst = w.color('reset')

# ================================[ checks ]===============================

# re-wrote this block to use hdata instead of infolist -@pX 03.28.2019
def is_url_listed(buffer, url, num):
    found = False
    hdata = w.hdata_get("buffer")
    lines = w.hdata_pointer(hdata, buffer, 'lines')
    lastline = w.hdata_pointer(w.hdata_get('lines'), lines, 'last_line')

    x = 0
    while x < int(num):
        data = w.hdata_pointer(w.hdata_get('line'), lastline, 'data')
        msg = w.hdata_string(w.hdata_get('line_data'), data, 'message')
        search = re.search(url, msg)

        if search:
            found = True
            break

        lastline = w.hdata_move(w.hdata_get('line'), lastline, -1)
        x += 1

    return found


# tinyurl ignore list from shortenurl.py - @pX 03.21.2019
def should_ignore_url(turl):
    ignorelist = fu_cg('url_ignore').split(',')

    for ignore in ignorelist:
        if len(ignore) > 0 and ignore in turl:
            return True

    return False


# tinyurl -@pX 03.19.2019
def get_shortened_url(turl):
    turl = TINYURL % urlencode({'url': turl})
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', SCRIPT_NAME + ' v' + SCRIPT_VERSION)]

    # avoid a possible tantrum by handling exceptions -@pX 3.28.2019
    try:
        turl = opener.open(turl).read()
    except (urllib2.HTTPError, urllib2.URLError):
        turl = False

    return turl


# ================================[ config related ]===============================

# config get -@pX 03.19.2019
def fu_cg(option):
    option = w.config_get_plugin(option)
    return option


# config set -@pX 03.19.2019
def fu_cs(option, value):
    w.config_set_plugin(option, value)


# color get
def c(color):
    return w.color(color)


# Set default if not found in plugins.conf
def initsettings():

    for option, value in SETTINGS.items():

        if not w.config_is_set_plugin(option):
            fu_cs(option, value[0])
            SETTINGS[option] = value[0]

        else:
            SETTINGS[option] = fu_cg(option)

        w.config_set_desc_plugin(option, value[1] + ' [default: ' + value[0] + ']')


# check for old config and import it, only once.
def isOld():

    if w.config_is_set_plugin('display_skip_check'):
        return w.WEECHAT_RC_OK

    if w.config_is_set_plugin('display_buffer_short_name'):
        if fu_cg('display_active_buffer'):
            fu_cs('show_active_buffer', fu_cg('display_active_buffer'))
        if fu_cg('display_private'):
            fu_cs('show_private', fu_cg('display_private'))
        if fu_cg('display_self'):
            fu_cs('show_self', fu_cg('display_self'))
        if fu_cg('display_own_color'):
            fu_cs('show_self_color', fu_cg('display_own_color'))
        if fu_cg('display_buffer_short_name'):
            fu_cs('show_buffer_short', fu_cg('display_buffer_short_name'))
        if fu_cg('display_buffer_short_name_color'):
            fu_cs('show_buffer_short_color', fu_cg('display_buffer_short_name_color'))
        fu_cs('display_skip_check', '1')

        MSA = ("%s*** ALERT ALERT ALERT ***%s\a\n"
                "You appear to be running an old version of %sfUrlbuf%s.\n"
                "Most options have changed.  I've done my best to import "
                "your previous config.\n"
                "Please look over '%s/fset furlbuf%s'.  Old options "
                "included '%sdisplay_%s' in the name.\n"
                "When you're good with the new settings, issue a "
                "'%s/save%s' to write config to memory.\n"
                % (c('red'), rst, c('blue'), rst,
                c('lightgreen'), rst, c('brown'), rst,
                c('lightgreen'), rst))

        MSB = ("If you're feeling saucey after the '%s/save%s', manually "
                "edit %s~/.weechat/plugins.conf%s and %sremove%s all lines "
                "starting with '%spython.furlbuf.display_%s'\n"
                "If you do this, make sure to '%s/save%s' and then '%s/reload%s'\n"
                "%sYou will not see this message again.%s"
                % (c('lightgreen'), rst, c('brown'), rst, c('red'),
                rst, c('brown'), rst, c('lightgreen'), rst,
                c('lightgreen'), rst, c('white'), rst))

        w.prnt(w.current_buffer(), MSA + MSB)

    return w.WEECHAT_RC_OK


# ================================[ important buffer sttuff - the core of it all ]===============================

# fnction to create buffer -@pX  03.17.2019
def furlbuf_buffer_create():
    global furlbuf_buffer
    furlbuf_buffer = w.buffer_search('python', 'fUrlbuf')

    if not furlbuf_buffer:
        furlbuf_buffer = w.buffer_new('fUrlbuf', 'furlbuf_input_cb', '', '', '')
        w.buffer_set(furlbuf_buffer, 'title', '-[' + SCRIPT_NAME + ' v' + SCRIPT_VERSION + ']- a neat url logger')
        w.buffer_set(furlbuf_buffer, 'notify', '0')
        w.buffer_set(furlbuf_buffer, 'nicklist', '0')

        # mark where we left off -@pX 03.16.2019
        if fu_cg('show_unread') == 'on':
            w.buffer_set(furlbuf_buffer, 'unread', '')

        # show a backlog when (re)creating the buffer -@pX  03.19.2019
        if furlbuf_buffer and fu_cg('show_backlog') == 'on':
            w.hook_signal_send("logger_backlog", w.WEECHAT_HOOK_SIGNAL_POINTER, furlbuf_buffer)


# dummy callback for input, user can only run commands in this buffer
def furlbuf_input_cb(data, buffer, input_data):
    return w.WEECHAT_RC_OK


# close the buffer
def furlbuf_close_cb(*kwargs):
    global furlbuf_buffer
    furlbuf_buffer = None
    return w.WEECHAT_RC_OK


# modify outgiong url if applicable - modified code from shortenurl.py -@pX 03.21.2019
def outgoing_hook(data, modifier, modifier_data, msg):

    url_short_own = fu_cg('url_short_own')
    max_url_length = int(fu_cg('url_length'))

    for url in urlRe.findall(msg):

        if fu_cg('url_shorten') == 'off' or url_short_own == 'off' or (len(url) <
                                        max_url_length or should_ignore_url(url)):
            return msg

        tiny_url = get_shortened_url(url)
        if tiny_url:
            msg = msg.replace(url, "[%(tiny_url)s] %(url)s " % dict(url=url, tiny_url=tiny_url))

    return msg


# process incoming messages
def furlbuf_print_cb(data, buffer, date, tags, displayed, highlight, prefix, message):

    nickcolor = fu_cg('show_nicks_color')
    buffername = w.buffer_get_string(buffer, 'short_name') + rst
    leftchar = w.color(fu_cg('output_left_color')) + fu_cg('output_left')
    rightchar = w.color(fu_cg('output_right_color')) + fu_cg('output_right') + rst
    sepchar = w.color(fu_cg('output_sep_color')) + fu_cg('output_sep') + rst

    # Exit if the wanted tag is not in the message
    # accounting for 'self_msg' (allows for self url catching) -@pX  03.16.2019
    tagslist = tags.split(",")
    if not 'notify_message' in tagslist:

        if 'self_msg' in tagslist:
            if fu_cg('show_self') == 'off':
                return w.WEECHAT_RC_OK
            else:
                nickcolor = fu_cg('show_self_color')

        if 'notify_private' in tagslist:
            if fu_cg('show_private') == 'off':
                return w.WEECHAT_RC_OK
            else:
                buffername = "%spriv" % (w.color(fu_cg('show_private_color')))

    buffer_short_name = str(w.buffer_get_string(buffer, 'short_name'))
    skips = set(fu_cg('skip_buffers').split(','))
    if buffer_short_name in skips:
        return w.WEECHAT_RC_OK

    if fu_cg('show_active_buffer') == 'off':
        if buffer_short_name == w.buffer_get_string(w.current_buffer(), 'short_name'):
            return w.WEECHAT_RC_OK

    # Process all URLs from the message
    for url in urlRe.findall(message):
        output = ''

        if fu_cg('skip_duplicates') == 'on':
            num = fu_cg('skip_duplicates_num')
            if is_url_listed(furlbuf_buffer, url, num):
                continue

        if should_ignore_url(url):
            continue

        # we've passed our tests, now lets get the nick -@pX  03.18.2019
        nick = ''
        my_nick = w.buffer_get_string(buffer, 'localvar_nick')
        for idx in range(len(tagslist)):
            if 'nick_' in tagslist[idx]:
                nick = tagslist[idx][5:]

        # tinyurl incoming urls -@pX 03.21.2019
        tinyout = ''
        if nick == my_nick or fu_cg('url_shorten') == 'off':
            w.WEECHAT_RC_OK

        else:
            max_url_length = int(fu_cg('url_length'))
            if len(url) > max_url_length and not should_ignore_url(url):
                tiny_url = get_shortened_url(url)

                if tiny_url:
                    tinyout = ("%s%s%s%s" % (leftchar,
                                w.color(fu_cg('url_color_tiny')), tiny_url, rightchar))

                # if a tinyurl wasn't present, append to original buffer -@pX 03.25.2019
                if 'tinyurl.com' not in message:
                    w.prnt(buffer, tinyout)

        # using nick instead of prefix to account for ACTION messages -@pX  03.18.2019
        if fu_cg('show_nicks') == 'on' and fu_cg('show_buffer_short') == 'on':
            output = ("%s%s%s%s%s" % (w.color(nickcolor), nick, sepchar,
                        w.color(fu_cg('show_buffer_short_color')), buffername))

        elif fu_cg('show_nicks') == 'on' and fu_cg('show_buffer_short') == 'off':
            output = "%s%s" % (w.color(nickcolor), nick)

        elif fu_cg('show_nicks') == 'off' and fu_cg('show_buffer_short') == 'on':
            output = "%s%s" % (w.color(fu_cg('show_buffer_short_color')), buffername)

        else:
            leftchar = ''
            rightchar = ''
            output = ''

        # If you close the buffer, you shouldn't have to reload the script to open it again, imo.. -@pX 03.17.2019
        # moved this check to occur just before the print instead of function start -@pX 03.17.2019
        if not furlbuf_buffer:
            furlbuf_buffer_create()

        # output to furlbuf_buffer
        w.prnt(furlbuf_buffer, leftchar + output + rightchar + url + ' ' + tinyout)

    return w.WEECHAT_RC_OK


# ================================[ main ]===============================

if __name__ == '__main__':
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, 'furlbuf_close_cb', ''):

        isOld()

        initsettings()

        furlbuf_buffer_create()

		# hook all public, private, and self messages -@pX 03.16.2019
        w.hook_print('', 'notify_message', '', 1, 'furlbuf_print_cb', '')
        w.hook_print('', 'notify_private', '', 1, 'furlbuf_print_cb', '')
        w.hook_print('', 'self_msg', '', 1, 'furlbuf_print_cb', '')
        # modify outgoing message with tinyurl if applicable
        w.hook_modifier('irc_out_privmsg', 'outgoing_hook', '')
