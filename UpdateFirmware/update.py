from __future__ import print_function
import subprocess
import socket
import sys
import os
import logging
import hashlib
import random

FLASH = 0
SPIFFS = 100
AUTH = 200
PROGRESS = False


def update_progress(progress):
    if PROGRESS:
        bar_length = 60  # Modify this to change the length of the progress bar
        status = ""
        if isinstance(progress, int):
            progress = float(progress)
        if not isinstance(progress, float):
            progress = 0
            status = "error: progress var must be float\r\n"
        if progress < 0:
            progress = 0
            status = "Halt...\r\n"
        if progress >= 1:
            progress = 1
            status = "Done...\r\n"
        block = int(round(bar_length * progress))
        text = "\rUploading: [{0}] {1}% {2}".format("=" * block + " " * (bar_length - block), int(progress * 100),
                                                    status)
        sys.stderr.write(text)
        sys.stderr.flush()
    else:
        sys.stderr.write('.')
        sys.stderr.flush()


def serve(remote_addr, local_addr, remote_port, local_port, password, filename, command=FLASH):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (local_addr, local_port)
    logging.info('Starting on %s:%s', str(server_address[0]), str(server_address[1]))
    try:
        sock.bind(server_address)
        sock.listen(1)
    except Exception:
        logging.error("Listen Failed")
        return 1

    # Check whether Signed Update is used.
    if os.path.isfile(filename + '.signed'):
        filename = filename + '.signed'
        file_check_msg = 'Detected Signed Update. %s will be uploaded instead.' % filename
        sys.stderr.write(file_check_msg + '\n')
        sys.stderr.flush()
        logging.info(file_check_msg)

    content_size = os.path.getsize(filename)
    f = open(filename, 'rb')
    file_md5 = hashlib.md5(f.read()).hexdigest()
    f.close()
    logging.info('Upload size: %d', content_size)
    message = '%d %d %d %s\n' % (command, local_port, content_size, file_md5)

    # Wait for a connection
    logging.info('Sending invitation to: %s', remote_addr)
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    remote_address = (remote_addr, int(remote_port))
    sock2.sendto(message.encode(), remote_address)
    sock2.settimeout(10)
    try:
        data = sock2.recv(128).decode()
    except Exception:
        logging.error('No Answer')
        sock2.close()
        return 1
    if data != "OK":
        if data.startswith('AUTH'):
            nonce = data.split()[1]
            cnonce_text = '%s%u%s%s' % (filename, content_size, file_md5, remote_addr)
            cnonce = hashlib.md5(cnonce_text.encode()).hexdigest()
            passmd5 = hashlib.md5(password.encode()).hexdigest()
            result_text = '%s:%s:%s' % (passmd5, nonce, cnonce)
            result = hashlib.md5(result_text.encode()).hexdigest()
            sys.stderr.write('Authenticating...')
            sys.stderr.flush()
            message = '%d %s %s\n' % (AUTH, cnonce, result)
            sock2.sendto(message.encode(), remote_address)
            sock2.settimeout(10)
            try:
                data = sock2.recv(32).decode()
            except Exception:
                sys.stderr.write('FAIL\n')
                logging.error('No Answer to our Authentication')
                sock2.close()
                return 1
            if data != "OK":
                sys.stderr.write('FAIL\n')
                logging.error('%s', data)
                sock2.close()
                sys.exit(1)
            sys.stderr.write('OK\n')
        else:
            logging.error('Bad Answer: %s', data)
            sock2.close()
            return 1
    sock2.close()

    logging.info('Waiting for device...')
    try:
        sock.settimeout(10)
        connection, client_address = sock.accept()
        sock.settimeout(None)
        connection.settimeout(None)
    except Exception:
        logging.error('No response from device')
        sock.close()
        return 1

    try:
        f = open(filename, "rb")
        if PROGRESS:
            update_progress(0)
        else:
            sys.stderr.write('Uploading')
            sys.stderr.flush()
        offset = 0
        while True:
            chunk = f.read(1460)
            if not chunk:
                break
            offset += len(chunk)
            update_progress(offset / float(content_size))
            connection.settimeout(10)
            try:
                connection.sendall(chunk)
                if connection.recv(32).decode().find('O') >= 0:
                    pass
            except Exception:
                sys.stderr.write('\n')
                logging.error('Error Uploading')
                connection.close()
                f.close()
                sock.close()
                return 1

        sys.stderr.write('\n')
        logging.info('Waiting for result...')
        # libraries/ArduinoOTA/ArduinoOTA.cpp L311 L320
        # only sends digits or 'OK'. We must not not close
        # the connection before receiving the 'O' of 'OK'
        try:
            connection.settimeout(60)
            received_ok = False
            received_error = False
            while not (received_ok or received_error):
                reply = connection.recv(64).decode()
                # Look for either the "E" in ERROR or the "O" in OK response
                # Check for "E" first, since both strings contain "O"
                if reply.find('E') >= 0:
                    sys.stderr.write('\n')
                    logging.error('%s', reply)
                    received_error = True
                elif reply.find('O') >= 0:
                    logging.info('Result: OK')
                    received_ok = True
            connection.close()
            f.close()
            sock.close()
            if received_ok:
                return 0
            return 1
        except Exception:
            logging.error('No Result!')
            connection.close()
            f.close()
            sock.close()
            return 1

    finally:
        connection.close()
        f.close()


if __name__ == '__main__':
    code_name = "display"
    arduino_build = f"./arduino-cli compile -b esp8266:esp8266:nodemcuv2 ./src/{code_name}/ --output-dir bin/{code_name}",

    result = subprocess.Popen(arduino_build, shell=True)
    result.wait()
    output, error = result.communicate()
    print(output)
    # ota = subprocess.Popen("./espota.py -i 192.168.0.136 -p 8266 -f bin/esp_test/esp_test.ino.bin", shell=True)
    # output, error = ota.communicate()
    # print(output)
    esp_ip = "192.168.0.136"
    host_ip = "0.0.0.0"
    esp_port = 8266
    host_port = random.randint(10000, 60000)
    auth = ""
    image = f"bin/{code_name}/{code_name}.ino.bin"
    command = FLASH
    serve(esp_ip, host_ip, esp_port, host_port, auth, image, command)
