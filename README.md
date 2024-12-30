# sd-webui-trust-http-header-user

This extension hacks around current limitations in the Automatic1111 SD webui
when it comes to external authentication. Namely, the only approach supported
is authenticating users against either a text file or a CLI argument containing
a static list of usernames and passwords.

It is easy to deploy a proxy in front of the web UI or API which does a bit
more clever authentication, if not authorization; namely, a proxy could perform
OpenID Connect login or similar (perhaps even more basic OAuth2), or Kerberos
SSO, or similar, and then pass on a header that would be easier for the
Gradio-based apps to understand.

This is the case with this extension: it assumes that `X-Forwarded-Email` and
`X-Forwarded-User` will be used to declare the identity of the user accessing
the web UI. These are ultimately trusted.

**Main purpose is attributing generated content to a logged in user.** The
actual authentication before a request is made is delegated to a fronting
proxy, and the proxy is ultimately trusted; it's not a security measure as much
as an attribution measure once you have the security measure deployed.

In case of [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/)
configured to perform login with Google's services, the `-User` header will
contain Google's internal numerical user ID, so the email is for now
preferred.

In future, a better identifier could be selected, and header names could be
configurable. Or, because this is implemented as a hacked-up middleware, this
could actually do full OAuth2 / OpenID Connect flow itself.

However, it is not urgent, as author finds it already beneficial to be able
to attribute activity to individual users who have access via the proxy
without having to resort to crude methods such as static logins.

## Why not Gradio `auth_dependency`?

As of 2024-12, webui is locked into Gradio 3.41.2 which doesn't seem to allow
overriding the login method in this way.

It also seems difficult to implement as an extension, and would require
changes to either `webui.py` to use `mount_gradio_app` instead of a
Gradio block's `.launch` (simultaneously dropping the direct use of `.launch`
which may have other consequences), or to ``modules/ui.py` to specify
`auth_dependency` there. However, neither approach seems to be feasible with
Gradio 3.41.2.

## Why not Starlette's user authentication middleware

While webui uses Gradio, meaning FastAPI, meaning Starlette, it does not
seem like Gradio uses Starlette's authentication nor authorization middleware,
and neither does webui try to do something about it.

It would be more difficult to do that than to hack into webui and Gradio.

## Brittle?

Yes, this is very brittle and dependent on very specific implementation
details.

Unfortunately, while Gradio offers login via OAuth, the default seems to be
mainly aiming at HuggingFace login and it does not seem feasible to upgrade
it to log in with something else, at least not with 3.41.2. However, needing
to enable this type of login seems to be related to the internals used by
this extension to track which session ID ('token') is which user.

Aside from this 'token' login tracking, the rest is just support for
low-level usernames and passwords, and this does not seem very extensible.

As long as the fronting proxy does not leak anything and doesn't allow the
user of the web UI to specify the email / user headers, this will be fine.

As long as the web UI doesn't change the way user information is tracked
internally ('token' and 'auth' structures), this will be fine.

## Code style?

Since this is just a hack to make _something_ work, there was no push for
any particular code style. Weird imports all over the place are an artefact
of looking at the code as is written in this space, rather than the usual
practice of just doing imports once, on top.

Cleanup was secondary.

No tests, since this is (again) a hack. A full integration test would be
needed.

