from machine import Pin, SPI, PWM
import framebuf

BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9


class LCD_1inch14(framebuf.FrameBuffer):

    keyA = Pin(15,Pin.IN,Pin.PULL_UP)
    keyB = Pin(17,Pin.IN,Pin.PULL_UP)
    keyUp = Pin(2 ,Pin.IN,Pin.PULL_UP)
    keyCenter = Pin(3 ,Pin.IN,Pin.PULL_UP)
    keyLeft = Pin(16 ,Pin.IN,Pin.PULL_UP)
    keyDown = Pin(18 ,Pin.IN,Pin.PULL_UP)
    keyRight = Pin(20 ,Pin.IN,Pin.PULL_UP)

    def __init__(self):
        self.width = 240
        self.height = 135

        # start modification: in the sample script this
        # was part of the __main__ logic
        pwm = PWM(Pin(BL))
        pwm.freq(1000)
        pwm.duty_u16(32768)  # max 65535
        # end of modification
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,10000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()
        
        self.red   =   0x07E0
        self.green =   0x001f
        self.blue  =   0xf800
        self.white =   0xffff
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize dispaly"""  
        self.rst(1)
        self.rst(0)
        self.rst(1)
        
        self.write_cmd(0x36)
        self.write_data(0x70)

        self.write_cmd(0x3A) 
        self.write_data(0x05)

        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)

        self.write_cmd(0xB7)
        self.write_data(0x35) 

        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)   

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6)
        self.write_data(0x0F) 

        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)

        self.write_cmd(0xE0)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)

        self.write_cmd(0xE1)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)
        
        self.write_cmd(0x21)

        self.write_cmd(0x11)

        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x28)
        self.write_data(0x01)
        self.write_data(0x17)
        
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x35)
        self.write_data(0x00)
        self.write_data(0xBB)
        
        self.write_cmd(0x2C)
        
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def keyAPressed(self):
        return self.keyA.value() == 0
    
    def keyBPressed(self):
        return self.keyB.value() == 0
    
    def keyUpPressed(self):
        return self.keyUp.value() == 0
    
    def keyDownPressed(self):
        return self.keyDown.value() == 0
    
    def keyLeftPressed(self):
        return self.keyLeft.value() == 0
    
    def keyRightPressed(self):
        return self.keyRight.value() == 0
    
    def keyCenterPressed(self):
        return self.keyCenter.value() == 0
    
    def registerKeyUpCallback(self, fn):
        # the wrapper function exists to swallow the "pin" argument
        def wrapperfn(pin):
            fn()
        self.keyUp.irq(trigger=Pin.IRQ_FALLING, handler=wrapperfn)
    
    def registerKeyDownCallback(self, fn):
        def wrapperfn(pin):
            fn()
        self.keyDown.irq(trigger=Pin.IRQ_FALLING, handler=wrapperfn)
    
    def registerKeyLeftCallback(self, fn):
        def wrapperfn(pin):
            fn()
        self.keyLeft.irq(trigger=Pin.IRQ_FALLING, handler=wrapperfn)
    
    def registerKeyRightCallback(self, fn):
        def wrapperfn(pin):
            fn()
        self.keyRight.irq(trigger=Pin.IRQ_FALLING, handler=wrapperfn)
