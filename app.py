import sys
import os
import platform
import shutil
import yaml

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QLabel,
    QMessageBox,
    QStackedWidget,
    QFormLayout,
    QFrame,
    QTextEdit
)
from PyQt5.QtCore import QProcess

CONFIG_FILE = 'config.yaml'

class ApkBuilderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('APK Builder GUI')
        self.resize(700, 550)

        # Initialize settings dictionary and load from file
        self.settings = {
            'dump_file': '',
            'dump_out': '',
            'pack_dir': '',
            'keystore_path': '',
            'keystore_pass': '',
            'keystore_out': '',
            'sdk_path': ''
        }
        self.load_settings()

        # Build the user interface and apply theme
        self.setup_ui()
        self.apply_dark_theme()

        # Prepare placeholders for the execution queue and state
        self.commands = []         # list of command lists to execute
        self.current_index = 0     # tracks which command is next
        self.built_apk = None      # path to intermediate built APK
        self.aligned_apk = None    # path to intermediate aligned APK

    def load_settings(self):
        """
        Load persisted settings from a YAML file. Ignore errors silently.
        """
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        self.settings.update(data)
            except Exception:
                pass  # if parsing fails, skip without breaking

    def save_settings(self):
        """
        Save current settings to a YAML file. Show warning on failure.
        """
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.settings, f)
        except Exception as e:
            QMessageBox.warning(self, 'Warning', f'Cannot save settings: {e}')

    def setup_ui(self):
        """
        Create and arrange all UI components: mode buttons, stacked pages,
        file selectors, Run button, and console output.
        """
        layout = QVBoxLayout(self)

        # Top row: Dump / Pack / Keystore mode selection
        mode_layout = QHBoxLayout()
        self.btn_dump = QPushButton('Dump')
        self.btn_pack = QPushButton('Pack')
        self.btn_keystore = QPushButton('Keystore')
        for btn in (self.btn_dump, self.btn_pack, self.btn_keystore):
            btn.setCheckable(True)
            mode_layout.addWidget(btn)
        self.btn_dump.setChecked(True)
        layout.addLayout(mode_layout)

        # Central area: stacked widget for each mode's form
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # --- Dump page ---
        dump_page = QWidget()
        df = QFormLayout(dump_page)
        self.dump_file_edit = QLineEdit(self.settings['dump_file'])
        df.addRow('APK File:', self.dump_file_edit)
        btn = QPushButton('Browse…')
        btn.clicked.connect(self.select_dump_file)
        df.addRow(btn)
        self.dump_out_edit = QLineEdit(self.settings['dump_out'])
        df.addRow('Output Folder:', self.dump_out_edit)
        self.stack.addWidget(dump_page)

        # --- Pack page ---
        pack_page = QWidget()
        pf = QFormLayout(pack_page)
        self.pack_dir_edit = QLineEdit(self.settings['pack_dir'])
        pf.addRow('Smali Project Folder:', self.pack_dir_edit)
        btn = QPushButton('Browse…')
        btn.clicked.connect(self.select_pack_dir)
        pf.addRow(btn)

        self.keystore_path_edit = QLineEdit(self.settings['keystore_path'])
        pf.addRow('Keystore File:', self.keystore_path_edit)
        btn = QPushButton('Browse…')
        btn.clicked.connect(self.select_keystore_file)
        pf.addRow(btn)

        self.keystore_pass_edit = QLineEdit(self.settings['keystore_pass'])
        self.keystore_pass_edit.setEchoMode(QLineEdit.Password)
        pf.addRow('Keystore Password:', self.keystore_pass_edit)

        self.stack.addWidget(pack_page)

        # --- Keystore generation page ---
        gen_page = QWidget()
        gf = QFormLayout(gen_page)
        self.ks_out_edit = QLineEdit(self.settings['keystore_out'])
        gf.addRow('Save Keystore To:', self.ks_out_edit)
        btn = QPushButton('Browse…')
        btn.clicked.connect(self.select_keystore_output)
        gf.addRow(btn)
        self.stack.addWidget(gen_page)

        # --- SDK root selector (optional) ---
        sdk_frame = QFrame()
        sf = QFormLayout(sdk_frame)
        self.sdk_path_edit = QLineEdit(self.settings['sdk_path'])
        self.sdk_path_edit.setPlaceholderText('Optional: Android SDK root')
        sf.addRow('SDK Root:', self.sdk_path_edit)
        btn = QPushButton('Browse…')
        btn.clicked.connect(self.select_sdk_root)
        sf.addRow(btn)
        layout.addWidget(sdk_frame)

        # Bottom: Run button and console output
        self.run_button = QPushButton('Run')
        self.run_button.clicked.connect(self.start_mode)
        layout.addWidget(self.run_button)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        # Connect mode buttons to page switching
        self.btn_dump.clicked.connect(lambda: self.switch_mode(0))
        self.btn_pack.clicked.connect(lambda: self.switch_mode(1))
        self.btn_keystore.clicked.connect(lambda: self.switch_mode(2))

    def apply_dark_theme(self):
        """
        Apply a simple dark stylesheet reminiscent of VS Code.
        """
        self.setStyleSheet(
            "QWidget{background:#1e1e1e;color:#d4d4d4;}"
            "QLineEdit,QTextEdit{background:#252526;color:#cccccc;}"
            "QPushButton{background:#3c3c3c;color:#d4d4d4;padding:4px;}"
            "QPushButton:checked{background:#0e639c;}"
        )

    def switch_mode(self, idx):
        """
        Highlight the selected mode button and show the
        corresponding stacked page.
        """
        self.btn_dump.setChecked(idx == 0)
        self.btn_pack.setChecked(idx == 1)
        self.btn_keystore.setChecked(idx == 2)
        self.stack.setCurrentIndex(idx)

    # --- File dialog callbacks (simple setters) ---
    def select_dump_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select APK', '', 'APK Files (*.apk)')
        if path:
            self.dump_file_edit.setText(path)
            self.settings['dump_file'] = path
            self.dump_out_edit.setText(os.path.dirname(path))
            self.settings['dump_out'] = os.path.dirname(path)

    def select_pack_dir(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Smali Project Folder')
        if path:
            self.pack_dir_edit.setText(path)
            self.settings['pack_dir'] = path

    def select_keystore_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Keystore', '', 'Keystore Files (*.jks *.keystore)')
        if path:
            self.keystore_path_edit.setText(path)
            self.settings['keystore_path'] = path

    def select_keystore_output(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save Keystore', 'mykeystore.jks', 'Keystore (*.jks)')
        if path:
            self.ks_out_edit.setText(path)
            self.settings['keystore_out'] = path

    def select_sdk_root(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Android SDK Root')
        if path:
            self.sdk_path_edit.setText(path)
            self.settings['sdk_path'] = path

    def start_mode(self):
        """
        Build the list of external commands based on the selected mode and
        kick off QProcess to run them sequentially.
        """
        # Disable Run button while processing
        self.run_button.setEnabled(False)
        self.console.clear()
        self.save_settings()  # persist user inputs

        mode = self.stack.currentIndex()
        s = self.settings
        self.commands = []
        self.current_index = 0
        self.built_apk = None
        self.aligned_apk = None

        # Locate apktool (jar or native) to avoid built-in PAUSE
        apktool = shutil.which('apktool') or shutil.which('apktool.bat')
        if not apktool:
            QMessageBox.critical(self, 'Error', 'Please install apktool and add to PATH.')
            self.run_button.setEnabled(True)
            return

        java = shutil.which('java')
        if apktool.lower().endswith('.bat') and java:
            # Prefer calling the .jar directly to skip pause
            jar = os.path.join(os.path.dirname(apktool), 'apktool.jar')
            executor = [java, '-jar', jar] if os.path.isfile(jar) else [apktool]
        else:
            executor = [apktool]

        if mode == 0:
            # Dump mode: apktool d
            apk, out = s['dump_file'], s['dump_out']
            if not apk or not out:
                QMessageBox.warning(self, 'Error', 'Please fill in Dump fields.')
                self.run_button.setEnabled(True)
                return
            target = os.path.normpath(os.path.join(out, os.path.splitext(os.path.basename(apk))[0]))
            os.makedirs(target, exist_ok=True)
            self.commands.append(executor + ['d', '-f', apk, '-o', target])

        elif mode == 1:
            # Pack mode: build → align → sign
            proj = s['pack_dir']
            ks = s['keystore_path']; ksp = s['keystore_pass']
            if not proj or not ks or not ksp:
                QMessageBox.warning(self, 'Error', 'Please fill in Pack fields.')
                self.run_button.setEnabled(True)
                return

            outdir = os.path.dirname(proj)
            apkname = os.path.splitext(os.path.basename(proj))[0] + '.apk'

            # 1) build APK
            built = os.path.normpath(os.path.join(outdir, apkname))
            self.built_apk = built
            self.commands.append(executor + ['b', proj, '-o', built])

            # 2) zipalign
            sdkroot = s['sdk_path']
            if sdkroot:
                bt = sorted(os.listdir(os.path.join(sdkroot, 'build-tools')), reverse=True)[0]
                tools = os.path.join(sdkroot, 'build-tools', bt)
                ext = '.exe' if platform.system() == 'Windows' else ''
                za = os.path.join(tools, 'zipalign' + ext)
                asgn = os.path.join(tools, 'apksigner' + ext)
            else:
                za, asgn = 'zipalign', 'apksigner'

            aligned = os.path.normpath(os.path.join(outdir, 'aligned_' + apkname))
            self.aligned_apk = aligned
            signed = os.path.normpath(os.path.join(outdir, 'signed_' + apkname))

            self.commands.append(self.wrap(za) + ['-v', '-p', '4', built, aligned])

            # 3) sign with apksigner (only --ks-pass needed)
            self.commands.append(self.wrap(asgn) + [
                'sign', '-v',
                '--ks', ks,
                '--ks-pass', f'pass:{ksp}',
                '--out', signed,
                aligned
            ])

        else:
            # Keystore gen: keytool command
            kout, alias, apw = s['keystore_out'], s['gen_alias'], s['gen_alias_pass']
            if not kout or not alias or not apw:
                QMessageBox.warning(self, 'Error', 'Please fill in Keystore fields.')
                self.run_button.setEnabled(True)
                return
            self.commands.append([
                'keytool', '-genkey', '-v',
                '-keystore', kout,
                '-alias', alias,
                '-keyalg', 'RSA',
                '-keysize', '2048',
                '-validity', '10000',
                '-storepass', apw,
                '-keypass', apw
            ])

        # Create a fresh QProcess for this run
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_output)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_process_error)

        # Start executing commands
        self.execute_next()

    def wrap(self, cmd):
        if isinstance(cmd, str):
            if ' ' in cmd and not cmd.startswith('"'):
                cmd = f'"{cmd}"'
            return ['cmd', '/c', cmd]
        return cmd

    def execute_next(self):
        """
        Launch the next command in the queue, or finish if done.
        """
        if self.current_index >= len(self.commands):
            QMessageBox.information(self, 'Done', 'All tasks completed')
            # Clean up intermediate APKs if in Pack mode
            if self.stack.currentIndex() == 1:
                if self.built_apk and os.path.isfile(self.built_apk):
                    os.remove(self.built_apk)
                if self.aligned_apk and os.path.isfile(self.aligned_apk):
                    os.remove(self.aligned_apk)
            self.run_button.setEnabled(True)
            return

        cmd = self.commands[self.current_index]
        # Display the command being run
        self.console.append('>> ' + ' '.join(cmd))
        # Start process asynchronously; callback on_finished will continue
        try:
            #self.process.start(cmd[0], cmd[1:])
            self.process.start(cmd[0], cmd[1:])
        except Exception as e:
            self.console.append(e)
        
        self.current_index += 1

    def on_output(self):
        """
        Append any non-empty stdout/stderr output to the console.
        """
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8')
            if data.strip():
                self.console.append(data)
        except Exception as e:
            self.console.append(f'> Error : {e}')

    def on_finished(self, exit_code, exit_status):
        """
        Called when a process finishes: log its exit code/status,
        then trigger the next command if any.
        """
        self.console.append(f"[Finished] exitCode={exit_code}, status={exit_status}")
        self.execute_next()
    
    def on_process_error(self, error):
        self.console.append(f"Process launched failed, type error: {error}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = ApkBuilderGUI()
    gui.show()
    sys.exit(app.exec_())