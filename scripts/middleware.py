#!/usr/bin/env python3

import gradio as gr
from modules import script_callbacks
from starlette import requests
from starlette import datastructures
from starlette import types


# https://stackoverflow.com/a/2257449/39974
import string
import random
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


class HeaderAuthMW:
    def __init__(self, app: types.ASGIApp, gradio_app_blocks: gr.Blocks) -> None:
        self.app = app
        self.blocks = gradio_app_blocks

    async def __call__(self, scope: types.Scope, receive: types.Receive, send: types.Send) -> None:
        if scope["type"] == "http" or scope["type"] == "websocket":  # pragma: no branch
            conn = requests.HTTPConnection(scope)
            headers = datastructures.Headers(scope=scope)
            if "Bearer" in headers.get("Authorization", ""):
                # we could extract access token from value[len('Bearer '):]
                pass
            user_h = headers.get("X-Forwarded-User", "")
            if user_h:
                # print("user: " + str(user_h))  # e.g. numeric id with G
                pass
            email_h = headers.get("X-Forwarded-Email", "")
            if email_h:
                # print("email: " + str(email_h))
                pass
            token_h = headers.get("X-Forwarded-Access-Token", "")
            if token_h:
                # print("token: " + str(token_h))
                pass

            if not headers.get('Authorization'):
                internal_identity = email_h or user_h # what do we use as the username in internal map?

                global glob_app
                auth_app = None
                if hasattr(self.app, 'auth'):
                    # expected not to be, this will be a middleware likely
                    auth_app = self.app
                elif hasattr(glob_app, 'auth'):
                    # probably this
                    auth_app = glob_app

                if internal_identity and auth_app:
                    #internal_identity = 'internal::' + internal_identity # <-- not using so the username is not overwritten

                    if not auth_app.auth: # <-- probably should be rmeoved
                        auth_app.auth = {}  # is this true in the gradio.routes.App object? (assuming it's what we have here)

                    # called a 'pw' but really it's a token that maps back to the identity.
                    # we will fill in the data structures to make it map back to the correct username, and populate a fake cookie quasi-sent by the browser.
                    # the rest is fluff.
                    #
                    # cookies are available via HTTPConnection(scope=scope).cookies and we will update them there
                    #
                    # no need to tell the browser via Set-Cookie as is done in Starlette's sessions middleware, since we don't want the browser to even know about this hack.
                    existing_pw = auth_app.auth.get(internal_identity, None) # <-- probably should be removed
                    pw = existing_pw

                    if not existing_pw:
                        # print('no existing internal pw, creating new one')
                        pw = id_generator(size=14)
                        auth_app.auth[internal_identity] = pw
                        auth_app.tokens[pw] = internal_identity

                    conn.cookies["access-token-unsecure"] = pw.encode('utf-8')
                    conn.cookies["access-token"] = pw.encode('utf-8')
                    # print(scope) # state before
                    # print(auth_app.tokens) # current 'user' database (mapping from token to username)

                    # probably useless: we should not update Authorization header since setting access-token or access-token-unsecure cookie is better.
                    # see routes.py in gradio 3.41.2.
                    # maybe API does care about it though.
                    import base64
                    new_auth_b = base64.b64encode(user_h.encode('utf-8') + b':' + pw.encode('utf-8'))
                    # headers[b'authorization'] = new_auth_b <--- does not work, cannot assign

                    jar: list[bytes] = []
                    for k in conn.cookies:
                        k: str
                        v: bytes | str = conn.cookies[k]
                        if isinstance(v, str):
                            v: bytes = v.encode('utf-8')
                        if b'\n' in v or b'\r' in v:
                            # do not pass on a cookie that has newlines (how did it even get here?)
                            continue
                        cookie = k.encode('utf-8') + b'=' + v
                        jar.append(cookie)

                    # assume utf8 valid for all cookies (printing only)

                    jar_b = b'; '.join(jar)
                    if False:
                        try:
                            jar_s = str(jar_b, 'utf-8')
                            # print(jar_s)
                        except Exception as e:
                            print('not utf8 in cookie jar (or similar): %s' % str(e))
                            # no need to interrupt, we are passing 'bytes' anyway so no need to encode, that was just for debug
                        # print(jar.output())

                    h = dict(scope['headers'])
                    h[b'cookie'] = jar_b
                    h[b'authorization'] = new_auth_b # likely not needed, but maybe for api access from cli?
                    scope['headers'] = [(k, v) for k, v in h.items()]

                    # print(scope) #  after modifications

                elif internal_identity:
                    print('cannot set internal identity, no auth in ' + str(self.app) + ' nor ' + str(glob_app))
            else:
                if email_h or user_h:
                    print(f'ignoring email/user in ({email_h}, {user_h}) as Authorization is already set)')

        # self.app is next_handler, i.e. likely a middleware
        await self.app(scope, receive, send)


glob_app = None

def on_app_started(gr_blocks, app):  # gr.Blocks, FastAPI
    global glob_app
    glob_app = app

    # starlette does not allow changing the middleware stack after startup.
    # however, initialize_util uses the hack of clearing away app.middleware_stack and then rebuilding it

    app.middleware_stack = None  # reset current middleware to allow modifying user provided list
    app.add_middleware(HeaderAuthMW, gradio_app_blocks=gr_blocks)
    app.build_middleware_stack()  # rebuild middleware stack on-the-fly


script_callbacks.on_app_started(on_app_started)

