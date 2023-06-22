

install:
	@pip install -r requirements.txt

serial:
	@sudo socat PTY,link=/dev/ttyS10 PTY,link=/dev/ttyS11

test:
	@python3 biofeedback-audio3.py


