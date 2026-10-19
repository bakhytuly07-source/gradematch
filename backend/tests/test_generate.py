from io import BytesIO
from tempfile import SpooledTemporaryFile

import numpy as np
from PIL import Image
import pytest

from app.color import decode_image, MAX_BYTES
from app.errors import ApiError
from test_api import assert_schema, image_bytes


@pytest.mark.parametrize('format', ['JPEG','PNG','WEBP'])
def test_format_signature_and_exact_limit(client, format):
    data = image_bytes(format)
    # The inclusive limit is byte-based and independent of declared MIME/name.
    data += b'\0' * (MAX_BYTES-len(data))
    result = assert_schema(client.post('/api/generate', files={'referenceFile': ('wrong.exe',data,'text/plain')}), 'StyleParams')
    assert set(result) == {'id','shadowTint','highlightTint','baseSaturation'}
    assert np.isfinite(result['shadowTint'] + result['highlightTint'] + [result['baseSaturation']]).all()


def test_orientation_and_decoded_pixel_limit():
    output = BytesIO()
    image = Image.new('RGB',(60,40),'red')
    exif = Image.Exif()
    exif[274] = 6
    image.save(output,format='JPEG',exif=exif)
    with decode_image(output.getvalue()) as decoded:
        assert decoded.size == (40,60)
    output = BytesIO()
    Image.new('1',(5000,5000)).save(output,format='PNG')
    with pytest.raises(ApiError) as error:
        decode_image(output.getvalue())
    assert error.value.status == 422


def test_failure_closes_uploads_without_disk_rollover(client,monkeypatch):
    import starlette.formparsers
    handles=[]
    def tracked(*args,**kwargs):
        handle=SpooledTemporaryFile(*args,**kwargs)
        handles.append(handle)
        return handle
    monkeypatch.setattr(starlette.formparsers,'SpooledTemporaryFile',tracked)
    payload=b'--x\r\nContent-Disposition: form-data; name="referenceFile"; filename="x.jpg"\r\n\r\n' + image_bytes('JPEG')
    # Even a complete valid image must not make an incomplete multipart acceptable.
    for body in [payload, payload+b'\r\n--x\r\nbad\r\n', payload+b'\0'*MAX_BYTES]:
        response=client.post('/api/generate',content=body,headers={'Content-Type':'multipart/form-data; boundary=x'})
        assert response.status_code in [413,422]
        assert_schema(response,'Error',response.status_code)
    assert handles and all(h.closed and not h._rolled for h in handles)


@pytest.mark.parametrize('data,status', [(b'',422),(b'GIF89a'+b'\0'*30,415),(b'\xff\xd8\xffcorrupt',422)])
def test_bad_uploads_use_error_envelope(client,data,status):
    assert_schema(client.post('/api/generate',files={'referenceFile':('x.jpg',data)}),'Error',status)


def test_analyzer_downscales_and_is_achromatic_for_gray(client,monkeypatch):
    import app.extraction as module
    original=module.np.asarray
    seen=[]
    def track(image,*args,**kwargs):
        seen.append(image.size)
        return original(image,*args,**kwargs)
    monkeypatch.setattr(module.np,'asarray',track)
    response=client.post('/api/generate',files={'referenceFile':('x.png',image_bytes('PNG',(2100,1100)))})
    assert response.status_code==200
    assert seen and max(seen[0])<=1024
