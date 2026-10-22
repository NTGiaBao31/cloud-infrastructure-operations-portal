from app.services.inventory import canonical_server_name, match_server


def test_instance_maps_to_web01(seeded):
    with seeded.app_context():
        server = match_server("192.168.10.11:9100")
        assert server is not None
        assert server.name == "WEB01"
        assert canonical_server_name("192.168.10.13:9182") == "WIN01"
        assert canonical_server_name("localhost:9090") == "MON01"
        assert canonical_server_name("192.168.10.10:9100") == "MON01"
