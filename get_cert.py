import socket
import ssl
import sys

def main():
    ip = "192.168.1.93"
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        
    print(f"Connecting to {ip}:443 to retrieve certificate...")
    
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((ip, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=ip) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)
                cert_pem = ssl.DER_cert_to_PEM_cert(cert_der)
                
                output_file = "sma_inverter.crt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(cert_pem)
                print(f"Successfully retrieved and saved certificate to {output_file}")
    except Exception as e:
        print(f"Error retrieving certificate: {e}")

if __name__ == "__main__":
    main()
