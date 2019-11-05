#coding:utf-8

import serial
import dcload
import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QColor
import time

def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

class SigSlot(QWidget):
    def __init__(self,parent=None):
        QWidget.__init__(self)

        self.dev = None
        self.model = None
        self.cur_range = None
        self.mode = None
        self.initalizing = True
        self.load_enabled = False

        self.setWindowTitle('ITECH Electric Load')

        self.dev_selector = QComboBox(self)
        self.dev_selector.addItems(serial_ports())
        # self.dev_selector.addItems(["COM7"])

        self.btn_connect = QPushButton('Open', self)
        self.btn_connect.clicked.connect(self.on_open_click)
        self.btn_connect.setToolTip('This is an example button')

        # Device Selector
        box_selector = QHBoxLayout()
        box_selector.addWidget(self.dev_selector)
        box_selector.addWidget(self.btn_connect)

        self.dev_id = QLineEdit(self)

        # Mode Zone
        mode_selector = QVBoxLayout()
        mode_group = QGroupBox("Mode", self)
        self.mode_cc = QRadioButton("CC")
        self.mode_cc.toggled.connect(lambda:self.on_mode_select(self.mode_cc))
        self.mode_cv = QRadioButton("CV")
        self.mode_cv.toggled.connect(lambda:self.on_mode_select(self.mode_cv))
        self.mode_cr = QRadioButton("CR")
        self.mode_cr.toggled.connect(lambda:self.on_mode_select(self.mode_cr))
        self.mode_cp = QRadioButton("CP")
        self.mode_cp.toggled.connect(lambda:self.on_mode_select(self.mode_cp))
        mode_selector.addWidget(self.mode_cc)
        mode_selector.addWidget(self.mode_cv)
        mode_selector.addWidget(self.mode_cr)
        mode_selector.addWidget(self.mode_cp)

        # Load Control        
        self.lcd = QLCDNumber(8, self)
        spRight = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        spRight.setHorizontalStretch(2)
        self.lcd.setSizePolicy(spRight)

        self.btn_load = QPushButton('LOAD', self)
        self.btn_load.clicked.connect(self.on_btn_load_clicked)


        # Power
        main_slider_label = QLabel("Power:", self)
        self.slider = QSlider(Qt.Horizontal,self)
        self.main_slider_value = QLineEdit("0.00A", self)
        self.main_slider_value.installEventFilter(self)
        # sp_slider_value = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # sp_slider_value.setHorizontalStretch(0.1)
        # self.main_slider_value.setSizePolicy(sp_slider_value)
        self.main_slider_value.setFixedSize(80, 20)
        self.slider.setMinimum(0)
        self.slider.setMaximum(10000 * 132)
        self.slider.setSingleStep(132*10000 / 300)

        # Meassure Zone Start
        mode_meas_vol = QGroupBox("Voltage", self)
        mode_meas_cur = QGroupBox("Current", self)
        mode_meas_pow = QGroupBox("Power", self)

        meas_vol_layout = QHBoxLayout()
        self.meas_vol_lcd = QLCDNumber(6, self)
        # get the palette
        palette = self.meas_vol_lcd.palette()
        palette.setColor(palette.Light, QColor(255, 0, 0))
        self.meas_vol_lcd.setPalette(palette)
        meas_vol_layout.addWidget(self.meas_vol_lcd)
        mode_meas_vol.setLayout(meas_vol_layout)

        meas_cur_layout = QHBoxLayout()
        self.meas_cur_lcd = QLCDNumber(6, self)
        palette = self.meas_cur_lcd.palette()
        palette.setColor(palette.Light, QColor(0, 255, 0))
        self.meas_cur_lcd.setPalette(palette)
        meas_cur_layout.addWidget(self.meas_cur_lcd)
        mode_meas_cur.setLayout(meas_cur_layout)

        meas_pow_layout = QHBoxLayout()
        self.meas_pow_lcd = QLCDNumber(6, self)
        palette = self.meas_pow_lcd.palette()
        palette.setColor(palette.Light, QColor(0, 0, 255))
        self.meas_pow_lcd.setPalette(palette)
        meas_pow_layout.addWidget(self.meas_pow_lcd)
        mode_meas_pow.setLayout(meas_pow_layout)

        meas_layout = QHBoxLayout()
        meas_layout.addWidget(mode_meas_vol)
        meas_layout.addWidget(mode_meas_cur)
        meas_layout.addWidget(mode_meas_pow)
        # Meassure Zone End

        # Pluse Zone
        pulse_mainLayout = QVBoxLayout()
        pulse_group = QGroupBox("Pluse", self)
        pulse_layout = QHBoxLayout()
        self.pulse_enabled = QCheckBox("ENABLE", self)
        self.pulse_freq = QSlider(Qt.Horizontal, self)
        self.pulse_freq.setMinimum(1)
        self.pulse_freq.setMaximum(5000)
        self.pulse_freq.setSingleStep(10)

        self.pulse_freq_text = QLineEdit("0.00Hz", self)
        self.pulse_freq_text.installEventFilter(self)
        self.pulse_freq_text.setFixedSize(60, 20)

        self.pulse_duty = QSlider(Qt.Horizontal, self)
        self.pulse_duty.setMinimum(50)
        self.pulse_duty.setMaximum(950)

        self.pulse_duty_text = QLineEdit("50.0%", self)
        self.pulse_duty_text.installEventFilter(self)
        self.pulse_duty_text.setFixedSize(40, 20)

        pulse_level_label = QLabel("Level:", self)
        self.pulse_level_slider = QSlider(Qt.Horizontal,self)
        self.pulse_level_text = QLineEdit("0.00A", self)
        self.pulse_level_text.installEventFilter(self)
        self.pulse_level_text.setFixedSize(40, 20)
        self.pulse_level_slider.setMinimum(0)
        self.pulse_level_slider.setMaximum(1000)

        pulse_layout.addWidget(self.pulse_enabled)
        pulse_layout.addWidget(self.pulse_freq)
        pulse_layout.addWidget(self.pulse_freq_text)
        pulse_layout.addWidget(self.pulse_duty)
        pulse_layout.addWidget(self.pulse_duty_text)

        pulse_level_layout = QHBoxLayout()
        pulse_level_layout.addWidget(pulse_level_label)
        pulse_level_layout.addWidget(self.pulse_level_slider)
        pulse_level_layout.addWidget(self.pulse_level_text)

        pulse_mainLayout.addLayout(pulse_layout)
        pulse_mainLayout.addLayout(pulse_level_layout)
        pulse_group.setLayout(pulse_mainLayout)

        self.pulse_enabled.toggled.connect(self.on_pulse_enabled_toggle)
        self.pulse_freq.valueChanged.connect(self.on_pulse_freq_slider_valueChanged)
        self.pulse_duty.valueChanged.connect(self.on_pulse_duty_slider_valueChanged)
        self.pulse_level_slider.valueChanged.connect(self.on_pulse_level_slider_valueChanged)
        # Pluse Zone End


        main_layout = QHBoxLayout()
        mode_group.setLayout(mode_selector)
        # mode_size = mode_group.sizeHint()
        # mode_size.setWidth(80)
        # mode_group.resize(mode_size)
        main_layout.addWidget(mode_group)
        main_layout.addWidget(self.lcd)
        self.btn_load.setFixedSize(self.btn_load.sizeHint().width(), mode_group.sizeHint().height())
        main_layout.addWidget(self.btn_load)

        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addWidget(self.dev_id)
        vbox.addLayout(main_layout)

        layer_main_slider = QHBoxLayout()
        layer_main_slider.addWidget(main_slider_label)
        layer_main_slider.addWidget(self.slider)
        layer_main_slider.addWidget(self.main_slider_value)        
        vbox.addLayout(layer_main_slider)

        vbox.addLayout(meas_layout)

        vbox.addWidget(pulse_group)

        self.setLayout(vbox)
         
        self.slider.valueChanged.connect(self.on_main_slider_valueChanged)
        self.resize(350,250)

        timer = QTimer(self)
        timer.setSingleShot(False)
        timer.timeout.connect(self.get_meas_value)
        timer.start(100)

    def get_main_scale_div(self):
        div_val = 10000

        return div_val

    def get_cmd(self, cmd):
        try:
            model = self.model.split(",")
            for i in range(0,len(COMMAND_SET)):
                if model[1] in COMMAND_SET[i]["models"]:
                    return COMMAND_SET[i][cmd]

            return COMMAND_SET[0][cmd]
        except Exception as e:
            return None

    @pyqtSlot()
    def get_meas_value(self):
        if self.dev is not None and not self.initalizing:
            try:
                state = self.dev.GetInputValues()
                self.meas_curr = state[1]
                self.meas_volt = state[0]
                self.meas_pow = state[2]

                self.load_enabled = (state[3] & 0x8) == 0x8
                self.update_load_button()

                self.meas_cur_lcd.display(self.meas_curr)
                self.meas_vol_lcd.display(self.meas_volt)
                self.meas_pow_lcd.display(self.meas_pow)
            except Exception as e:
                print("Read data failed")

    def update_mode(self):
        div_val = self.get_main_scale_div()
        
        if self.mode == "CC":
            max_var = self.dev.GetMaxCurrent()
            self.slider.setMaximum(max_var * div_val)
            self.slider.setSingleStep(max_var * div_val / 300)

            self.cur_current = self.dev.GetCCCurrent()
            self.slider.setValue(float(self.cur_current) * div_val)
            self.pulse_enabled.setEnabled(True)
        elif self.mode == "CV":
            max_var = self.dev.GetMaxVoltage()
            self.slider.setMaximum(max_var * div_val)
            self.slider.setSingleStep(max_var * div_val / 300)
            
            self.cur_voltage = self.dev.GetCVVoltage()
            self.slider.setValue(float(self.cur_voltage) * div_val)
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CP":
            max_var = self.dev.GetMaxPower()
            self.slider.setMaximum(max_var * div_val)
            self.slider.setSingleStep(max_var * div_val / 300)
            
            self.cur_power = self.dev.GetCWPower()
            self.slider.setValue(float(self.cur_power) * div_val)
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CR":
            max_var = 7500
            self.slider.setMaximum(max_var * div_val)
            self.slider.setSingleStep(max_var * div_val / 300)
            
            self.cur_resister = self.dev.GetCRResistance()
            self.slider.setValue(float(self.cur_resister) * div_val)
            self.pulse_enabled.setEnabled(False)
        self.update_slider_value()

    @pyqtSlot()
    def on_open_click(self):
        print("Click", self.dev_selector.currentText())
        if self.dev is None:
            self.initalizing = True
            self.dev = dcload.DCLoad()
            self.dev.Initialize(self.dev_selector.currentText(), 115200)
            self.btn_connect.setText("Close")
            self.model, serial_no, fw = self.dev.GetProductInformation()
            self.dev_id.setText(self.model)

            mode = self.dev.GetMode()
            self.mode = mode
            if mode == "CC":
                self.mode_cc.setChecked(True)
            elif mode == "CV":
                self.mode_cv.setChecked(True)
            elif mode == "CR":
                self.mode_cr.setChecked(True)
            elif mode == "CP":
                self.mode_cp.setChecked(True)

            self.update_mode()

            self.dev.SetRemoteControl()

            # self.dev.write("PULSe:FREQuency?")
            # self.cur_pulse_freq = self.dev.read().strip()
            # self.dev.write("PULSe:DCYCle?")
            # self.cur_pulse_duty = self.dev.read().strip()
            # self.dev.write("PULSe:LEVel:PERCentage:CURRent?")

            trans_state = self.dev.GetTransient(self.mode)
            self.trans_state = trans_state
            if trans_state[1] + trans_state[3] == 0:
                self.cur_pulse_freq = 10000
                self.cur_pulse_duty = 50
            else:
                self.cur_pulse_freq = 1 / (trans_state[1] + trans_state[3])
                self.cur_pulse_duty = trans_state[1] / (trans_state[1] + trans_state[3]) * 100
            self.cur_pulse_level = trans_state[0] / (self.slider.value()/self.get_main_scale_div()) * 100

            cur_function = self.dev.GetFunction()
            if cur_function == "transient":
                self.cur_pulse_enabled = True
            else:
                self.cur_pulse_enabled = False
            print("Pluse Freq : %s  DUTY: %s%%" % (self.cur_pulse_freq, self.cur_pulse_duty))
            self.update_pulse_info()

            self.initalizing = False
        else:
            del self.dev
            self.btn_connect.setText("Open")
            self.dev = None
            self.initalizing = True

    def update_pulse_info(self):
        duty_1 = 1 / self.cur_pulse_freq * (self.cur_pulse_duty / 100)
        duty_2 = 1 / self.cur_pulse_freq * (1 - self.cur_pulse_duty / 100)
        print(self.mode, self.cur_pulse_level / 100 * self.slider.value()/self.get_main_scale_div(), int(duty_1 * 10000), self.slider.value()/self.get_main_scale_div(), int(10000*duty_2))
        self.dev.SetTransient(self.mode, self.cur_pulse_level / 100 * self.slider.value()/self.get_main_scale_div(), duty_1, self.slider.value()/self.get_main_scale_div(), duty_2, "continuous")

        self.pulse_freq.setValue(float(self.cur_pulse_freq))
        self.pulse_duty.setValue(float(self.cur_pulse_duty) * 10)
        self.pulse_level_slider.setValue(float(self.cur_pulse_level) * 10)
        self.pulse_freq_text.setText("%.0fHz" % (float(self.cur_pulse_freq)))
        self.pulse_duty_text.setText("%.01f%%" % (float(self.cur_pulse_duty)))
        self.pulse_level_text.setText("%.01f%%" % (float(self.cur_pulse_level)))
        if self.cur_pulse_enabled:
            self.pulse_enabled.setChecked(True)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)
        else:
            self.pulse_enabled.setChecked(False)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)

    @pyqtSlot()
    def on_pulse_enabled_toggle(self):
        if not self.initalizing:
            self.cur_pulse_enabled = not self.cur_pulse_enabled
            if self.cur_pulse_enabled:
                self.dev.SetFunction("transient")
                print(self.dev.GetTriggerSource())
                self.dev.TriggerLoad()
            else:
                self.dev.SetFunction("fixed")
            print("Set Pluse To %s" % (self.cur_pulse_enabled))
            self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_freq_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Frequence to %d" % (self.pulse_freq.value()))
        self.cur_pulse_freq = self.pulse_freq.value()
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_duty_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Duty to %.01f%%" % (self.pulse_duty.value()/10))
        self.cur_pulse_duty = self.pulse_duty.value()/10
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_level_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Level to %.01f%%" % (self.pulse_level_slider.value()/10))
        self.cur_pulse_level = (self.pulse_level_slider.value()/10)
        self.update_pulse_info()

    @pyqtSlot()
    def on_mode_select(self,b):
        if b.isChecked() and not self.initalizing:
            print("Set MODE = %s  %d" % (b.text(), b.isChecked()))
            self.get_cmd("SET_MODE_FN")(self,b.text())
            self.mode = b.text()
            self.update_mode()

    def update_slider_value(self):
        div_val = self.get_main_scale_div()
        
        self.lcd.display("%.03f" % (self.slider.value()/div_val))

        if self.mode == "CC":
            self.main_slider_value.setText("%.03f A" % (self.slider.value()/div_val))
        elif self.mode == "CV":
            self.main_slider_value.setText("%.04f V" % (self.slider.value()/div_val))
        elif self.mode == "CP":
            self.main_slider_value.setText("%.04f W" % (self.slider.value()/div_val))
        elif self.mode == "CR":
            self.main_slider_value.setText("%.04f Ω" % (1/(self.slider.value()/div_val) if (self.slider.value()/div_val) > 0 else 7500))

    @pyqtSlot()
    def on_main_slider_valueChanged(self):
        div_val = self.get_main_scale_div()
        
        if self.initalizing:
            return
        print("Set Power to %d" % (self.slider.value()))
        self.update_slider_value()
        if self.mode == "CC":
            self.dev.SetCCCurrent(self.slider.value()/div_val)
        elif self.mode == "CV":
            self.dev.SetCVVoltage(self.slider.value()/div_val)
        elif self.mode == "CP":
            self.dev.SetCWPower(self.slider.value()/div_val)
        elif self.mode == "CR":
            self.dev.SetCRResistance(self.slider.value()/div_val)

    def eventFilter(self, obj, event):
        if obj == self.main_slider_value and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    div_val = self.get_main_scale_div()
                    if self.mode == "CR" and float(self.main_slider_value.text()) * div_val > 0:
                        self.slider.setValue(1/float(self.main_slider_value.text()) * div_val)
                    else:
                        self.slider.setValue(float(self.main_slider_value.text()) * div_val)

                    self.on_main_slider_valueChanged()
                    self.main_slider_value.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_slider_value()
            elif event.key() == Qt.Key_Escape:
                self.update_slider_value()
        elif obj == self.pulse_freq_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_freq.setValue(float(self.pulse_freq_text.text()))
                    self.pulse_freq_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif obj == self.pulse_duty_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_duty.setValue(float(self.pulse_duty_text.text()) * 10)
                    self.pulse_duty_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif obj == self.pulse_level_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_level_slider.setValue(float(self.pulse_level_text.text()) * 10)
                    self.pulse_level_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif event.type() == QEvent.Enter and obj in [self.main_slider_value, self.pulse_freq_text, self.pulse_duty_text, self.pulse_level_text]:
            rc = super(SigSlot, self).eventFilter(obj, event)
            obj.setFocus()
            obj.selectAll()
            return rc
        #     print(obj)
        return super(SigSlot, self).eventFilter(obj, event)

    def update_load_button(self):
        if self.load_enabled == False:
            self.btn_load.setStyleSheet("background-color: #00ff77;")
            self.mode_cc.setEnabled(True)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)
        else:
            self.btn_load.setStyleSheet("background-color: red;")
            self.mode_cc.setEnabled(False)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)

    @pyqtSlot()
    def on_btn_load_clicked(self):
        if self.initalizing:
            return
        print("Change Load State")
        if self.load_enabled == False:
            self.dev.TurnLoadOn()
            self.load_enabled = True
        else:
            print("Close LOAD")
            self.dev.TurnLoadOff()
            self.load_enabled = False

        self.update_load_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_load_clicked()

app = QApplication(sys.argv)
qb = SigSlot()
qb.show()
sys.exit(app.exec_())