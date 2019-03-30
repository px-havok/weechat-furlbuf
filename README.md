# _fUrlbuf_ - a neat url logger with tinyurl
**FUrlbuf** stands for Fork of _Urlbuf_.  The original _Urlbuf_ code is copyright stands @jkesanen.

When run under weechat, this script will:
- Log all incoming and outgoing URL's to a private buffer
- Associate a Tinyurl to all incoming and outgoing URL's if applicable

**If you are using _urlbuf.py_ and/or _shortenurl.py_, please make sure to unload them first.  This replaces both.
If you use a different URL shortening service, sorry!  Let me know and I can add others, or you can add them. ;)**

At this point I've rewritten most of the original Urlbuf and added some Tinyurl elements from shortenurl.py.
Urlbuf.py and Shortenurl.py were both replicating a lot of the same work on each hook, combining the 2 makes
sense and performance is better.

**Some** (but not all) **updates I made**:
- Using the 'nick_' tag instead of 'prefix' to prevent issues when the message is an **ACTION** (ex: /me <url>)
- Rebuilt is_url_listed() to use hdata instead of infolist per weechat developer recommendations.
- Added Tinyurl functionality for incoming and outgoing URL's.
- Added option to allow self url logging
- Default formatted output to: \[\<nick\> \/ \<buffer\>\] \<url\>
  - buffer = 'priv' if private message
  - brackets and separator are cutomizable
- Color the output
  - separate color for own nick so you 'stand out'
- Added 'unread marker' to see where you left off
  
## Contact me
I'm in #pX on EFnet, or email me px at havok.org.
