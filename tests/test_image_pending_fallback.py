import json
from pathlib import Path
from unittest.mock import patch

import pytest

from crawler.core.image_downloader import ImageDownloader


@pytest.mark.parametrize('status', ['failed:403', 'failed:404', 'error:timeout'])
def test_failed_image_uses_placeholder_without_poisoning_master_cache(tmp_path, status):
    downloader = ImageDownloader.__new__(ImageDownloader)
    downloader.versions_dir = tmp_path / 'versions'
    downloader.master_images_dir = tmp_path / 'master/images/products'
    downloader.master_images_dir.mkdir(parents=True)
    version = downloader.versions_dir / 'sample'
    version.mkdir(parents=True)
    (version / 'products.json').write_text(json.dumps([{
        'product_id': 12133, 'local_image_path': 'images/products/12133.jpg',
    }]))
    (version / 'manifest.json').write_text(json.dumps({'stats': {}}))
    with patch.object(downloader, '_download_single_image', return_value=(status, None)), \
         patch('crawler.core.image_downloader.time.sleep'):
        result = downloader.download_for_version('sample')
    product = json.loads((version / 'products.json').read_text())[0]
    asset = version / product['local_image_path']
    assert asset.is_file()
    assert product['image_hash'] == downloader._calculate_hash(asset)
    assert product['image_status'] == f'placeholder:{status}'
    assert result['failed_products'] == [{'product_id': 12133, 'error': status}]
    assert not (downloader.master_images_dir / '12133.jpg').exists()


def test_upstream_recovery_replaces_placeholder_and_populates_real_cache(tmp_path):
    from unittest.mock import Mock
    downloader = ImageDownloader.__new__(ImageDownloader)
    downloader.master_images_dir = tmp_path / 'master'
    downloader.master_images_dir.mkdir()
    version = tmp_path / 'version'
    version.mkdir()
    (version / '12133.jpg').write_bytes(b'old placeholder')
    content = (Path(__file__).resolve().parents[1] / 'crawler/assets/image-pending.jpg').read_bytes()
    downloader.session = Mock()
    downloader.session.get.return_value = Mock(status_code=200, content=content)
    status, image_hash = downloader._download_single_image(
        {'product_id': 12133, 'image_url': 'https://example.test/product.jpg'}, version)
    assert status == 'downloaded'
    assert (version / '12133.jpg').read_bytes() == content
    assert (downloader.master_images_dir / '12133.jpg').read_bytes() == content
    assert image_hash == downloader._calculate_hash(version / '12133.jpg')
