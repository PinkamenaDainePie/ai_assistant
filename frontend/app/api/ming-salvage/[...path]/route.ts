import type { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const UPSTREAM = (process.env.MING_SALVAGE_PROXY_URL || 'http://127.0.0.1:8010').replace(
  /\/+$/,
  '',
);

function passthroughStream(upstream: Response): ReadableStream<Uint8Array> {
  const reader = upstream.body!.getReader();
  return new ReadableStream({
    async pull(controller) {
      const { done, value } = await reader.read();
      if (done) {
        controller.close();
        return;
      }
      if (value) controller.enqueue(value);
    },
    cancel() {
      void reader.cancel();
    },
  });
}

async function proxy(request: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params.path?.join('/') || '';
  const search = request.nextUrl.search;
  const target = `${UPSTREAM}/${subpath}${search}`;

  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('connection');

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    // @ts-expect-error Node fetch streaming request body
    duplex: hasBody ? 'half' : undefined,
    cache: 'no-store',
  });

  const outHeaders = new Headers(upstream.headers);
  outHeaders.set('Cache-Control', 'no-cache, no-transform');
  outHeaders.delete('content-length');
  if (outHeaders.get('content-type')?.includes('text/event-stream')) {
    outHeaders.set('X-Accel-Buffering', 'no');
  }

  if (!upstream.body) {
    return new Response(await upstream.text(), {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: outHeaders,
    });
  }

  return new Response(passthroughStream(upstream), {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
