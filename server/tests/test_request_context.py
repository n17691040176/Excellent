from types import SimpleNamespace

from app.utils.request_context import build_payment_request_context, get_request_client_ip


def _request(headers=None, peer='192.0.2.1', **extra):
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host=peer) if peer is not None else None,
        **extra,
    )


def test_x_real_ip_is_preferred_over_forwarded_and_peer():
    request = _request(
        {
            'X-Real-IP': '198.51.100.7',
            'X-Forwarded-For': '203.0.113.8, 203.0.113.9',
        }
    )

    assert get_request_client_ip(request) == '198.51.100.7'


def test_x_forwarded_for_uses_first_valid_address():
    request = _request(
        {
            'x-real-ip': 'not-an-ip',
            'x-forwarded-for': 'also-invalid, 2001:0db8::2, 203.0.113.8',
        }
    )

    assert get_request_client_ip(request) == '2001:db8::2'


def test_invalid_headers_fall_back_to_socket_peer():
    request = _request(
        {
            'x-real-ip': 'invalid',
            'x-forwarded-for': 'unknown, 999.999.999.999',
        },
        peer='198.51.100.12',
    )

    assert get_request_client_ip(request) == '198.51.100.12'


def test_ipv6_peer_is_supported():
    request = _request({}, peer='2001:db8:0:0:0:0:0:3')

    assert get_request_client_ip(request) == '2001:db8::3'


def test_user_agent_is_trimmed_and_capped_at_512_characters():
    request = _request(
        {'x-real-ip': '203.0.113.15', 'user-agent': f'  browser-{"x" * 600}  '}
    )

    context = build_payment_request_context(request)

    assert context['client_ip'] == '203.0.113.15'
    assert len(context['user_agent']) == 512
    assert context['user_agent'].startswith('browser-')


def test_json_request_payload_cannot_override_network_ip():
    request = _request(
        {},
        peer='192.0.2.44',
        request_payload={'client_ip': '203.0.113.99', 'payer_client_ip': '203.0.113.99'},
        json={'client_ip': '203.0.113.99'},
    )

    assert build_payment_request_context(request) == {'client_ip': '192.0.2.44'}

