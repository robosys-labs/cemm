from cemm.web_demo import CEMMHandler, HTTPServer


if __name__ == "__main__":
    port = 5000
    print(f"CEMM Web Demo running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    server = HTTPServer(("127.0.0.1", port), CEMMHandler)
    server.serve_forever()
