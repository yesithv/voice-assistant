try:
    import truststore
    truststore.inject_into_ssl()  # use system CA certificates instead of bundled ones
except ImportError:
    pass
