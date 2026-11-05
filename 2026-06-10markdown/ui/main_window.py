"""主窗口。"""

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from converters import get_converter
from converters.md_to_docx_converter import MdToDocxConverter
from ui.settings_dialog import SettingsDialog
from utils.file_utils import get_file_info

# ─── 样式常量 ────────────────────────────────────────────────

DROP_STYLE_DEFAULT = """
    QLabel {
        border: 2px dashed #999; border-radius: 8px;
        font-size: 14px; color: #777; background: #fafafa;
    }
"""
DROP_STYLE_HOVER = """
    QLabel {
        border: 2px dashed #4a9eff; border-radius: 8px;
        font-size: 14px; color: #4a9eff; background: #f0f7ff;
    }
"""
SUCCESS_COLOR = 'color: #27ae60; font-size: 12px;'
INFO_COLOR    = 'color: #888; font-size: 12px;'
WARN_COLOR    = 'color: #e67e22; font-size: 12px;'
ERROR_COLOR   = 'color: #c0392b; font-size: 12px;'

FILE_FILTER = (
    '所有支持的文件 (*.docx *.pdf *.pptx *.html *.htm *.txt *.md);;'
    'Word 文档 (*.docx);;PDF 文档 (*.pdf);;'
    'PowerPoint (*.pptx);;HTML 文件 (*.html *.htm);;'
    '文本文件 (*.txt);;Markdown 文件 (*.md);;'
    '所有文件 (*.*)'
)


class ConvertWorker(QThread):
    """后台转换线程，避免 UI 卡顿。"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, converter, file_path: str, options: dict):
        super().__init__()
        self.converter = converter
        self.file_path = file_path
        self.options = options

    def run(self):
        try:
            result = self.converter.convert(self.file_path, self.options)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主应用程序窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Markdown 转换器')
        self.setMinimumSize(700, 550)
        self.resize(800, 650)

        self.current_file: str | None = None
        self.current_markdown: str = ''
        self._conversion_direction: str = 'to_markdown'  # 'to_markdown' | 'from_markdown'
        self.settings: dict = {
            'max_image_width': 800,
            'code_block_style': 'fenced',
        }
        self.worker: ConvertWorker | None = None

        self._setup_ui()
        self._setup_menu()

    # ─── UI 构建 ──────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)

        # 拖放区
        self.drop_label = QLabel('将文件拖放到此处\n或点击"选择文件"')
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(80)
        self.drop_label.setStyleSheet(DROP_STYLE_DEFAULT)
        self.drop_label.setAcceptDrops(True)
        self.drop_label.dragEnterEvent = self._drag_enter_event
        self.drop_label.dragLeaveEvent = self._drag_leave_event
        self.drop_label.dropEvent = self._drop_event
        root.addWidget(self.drop_label)

        # 文件信息
        self.file_info_label = QLabel('未选择文件')
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info_label.setStyleSheet(INFO_COLOR)
        root.addWidget(self.file_info_label)

        # 按钮行
        btn_layout = QHBoxLayout()

        self.select_btn = QPushButton('📂 选择文件')
        self.select_btn.clicked.connect(self._select_file)
        btn_layout.addWidget(self.select_btn)

        self.settings_btn = QPushButton('⚙ 设置')
        self.settings_btn.clicked.connect(self._open_settings)
        btn_layout.addWidget(self.settings_btn)

        self.convert_btn = QPushButton('🔄 转换')
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._convert)
        self.convert_btn.setStyleSheet('QPushButton { font-weight: bold; }')
        btn_layout.addWidget(self.convert_btn)

        btn_layout.addStretch()
        root.addLayout(btn_layout)

        # 状态
        self.status_label = QLabel('')
        self.status_label.setStyleSheet(INFO_COLOR)
        root.addWidget(self.status_label)

        # Markdown 预览
        self.preview = QPlainTextEdit()
        self.preview.setPlaceholderText('转换结果将在此显示...')
        self.preview.setStyleSheet("""
            QPlainTextEdit {
                font-family: "Consolas", "Microsoft YaHei", monospace;
                font-size: 13px;
            }
        """)
        root.addWidget(self.preview, stretch=1)

        # 底部操作按钮
        action_layout = QHBoxLayout()

        self.edit_toggle_btn = QPushButton('✏ 编辑')
        self.edit_toggle_btn.setCheckable(True)
        self.edit_toggle_btn.setEnabled(False)
        self.edit_toggle_btn.clicked.connect(self._toggle_edit)
        action_layout.addWidget(self.edit_toggle_btn)

        self.copy_btn = QPushButton('📋 复制到剪贴板')
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        action_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton('💾 另存为...')
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_as)
        action_layout.addWidget(self.save_btn)

        self.export_word_btn = QPushButton('📄 导出为 Word')
        self.export_word_btn.setEnabled(False)
        self.export_word_btn.clicked.connect(self._export_to_word)
        action_layout.addWidget(self.export_word_btn)

        action_layout.addStretch()
        root.addLayout(action_layout)

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&文件')

        open_action = QAction('&打开...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._select_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction('退&出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # ─── 拖放 ──────────────────────────────────────────────────

    def _drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()
            self.drop_label.setStyleSheet(DROP_STYLE_HOVER)

    def _drag_leave_event(self, event):
        self.drop_label.setStyleSheet(DROP_STYLE_DEFAULT)

    def _drop_event(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self._load_file(urls[0].toLocalFile())
        self.drop_label.setStyleSheet(DROP_STYLE_DEFAULT)

    # ─── 文件处理 ──────────────────────────────────────────────

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择文件', '', FILE_FILTER,
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        info = get_file_info(file_path)
        if info['format'] is None:
            QMessageBox.warning(
                self, '不支持的格式',
                f'文件 "{info["name"]}" 不是支持的格式。\n\n'
                f'支持：.docx, .pdf, .pptx, .html, .htm, .txt, .md',
            )
            return

        self.current_file = file_path
        self.current_markdown = ''
        self.preview.clear()
        self._conversion_direction = info['direction'] or 'to_markdown'

        self.convert_btn.setEnabled(True)
        self.copy_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.edit_toggle_btn.setEnabled(False)
        self.export_word_btn.setEnabled(False)
        self.status_label.setText('')

        self.file_info_label.setText(
            f'{info["name"]}  —  {info["format"]}  —  {info["size_display"]}'
        )

        # 根据文件类型更新 UI 提示
        if self._conversion_direction == 'from_markdown':
            self.convert_btn.setText('🔄 转为 Word')
            self.preview.setReadOnly(True)
            # 加载并显示 Markdown 文件内容
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    md_content = f.read()
                self.preview.setPlainText(md_content)
                self.current_markdown = md_content
                self.edit_toggle_btn.setEnabled(True)
                self.export_word_btn.setEnabled(True)
            except Exception:
                self.preview.setPlaceholderText('无法读取文件内容...')
        else:
            self.convert_btn.setText('🔄 转换')
            self.preview.setReadOnly(True)
            self.preview.setPlaceholderText('转换结果将在此显示...')

        if info['size_bytes'] > 100 * 1024 * 1024:
            QMessageBox.information(
                self, '文件较大',
                '该文件超过 100 MB，转换可能需要较长时间。',
            )

    # ─── 转换 ──────────────────────────────────────────────────

    def _convert(self):
        if not self.current_file:
            return

        self.convert_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.status_label.setText('正在转换...')
        self.status_label.setStyleSheet(WARN_COLOR)

        # 断开旧信号防止泄漏
        if self.worker is not None:
            try:
                self.worker.finished.disconnect()
                self.worker.error.disconnect()
            except TypeError:
                pass  # 没有连接信号

        if self._conversion_direction == 'from_markdown':
            # Markdown → Word
            self.worker = ConvertWorker(MdToDocxConverter(), self.current_file, self.settings)
        else:
            converter = get_converter(self.current_file)
            self.worker = ConvertWorker(converter, self.current_file, self.settings)

        self.worker.finished.connect(self._on_conversion_finished)
        self.worker.error.connect(self._on_conversion_error)
        self.worker.start()

    def _on_conversion_finished(self, result: str):
        if self._conversion_direction == 'from_markdown':
            # MD → Word: result is the output .docx path
            self.preview.setPlainText(f'Word 文档已生成：\n{result}')
            self.current_markdown = ''
            self.copy_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.edit_toggle_btn.setEnabled(False)
            self.export_word_btn.setEnabled(False)
            self.status_label.setText(f'Word 文档已保存至 {os.path.basename(result)} ✓')
            self.status_label.setStyleSheet(SUCCESS_COLOR)
        else:
            self.current_markdown = result
            self.preview.setPlainText(result)
            self.copy_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.edit_toggle_btn.setEnabled(True)
            self.export_word_btn.setEnabled(True)
            self.status_label.setText('转换完成 ✓')
            self.status_label.setStyleSheet(SUCCESS_COLOR)
        self.convert_btn.setEnabled(True)
        self.select_btn.setEnabled(True)

    def _on_conversion_error(self, error_msg: str):
        self.convert_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.status_label.setText(f'错误：{error_msg}')
        self.status_label.setStyleSheet(ERROR_COLOR)
        QMessageBox.critical(self, '转换失败', f'转换过程中出现错误：\n\n{error_msg}')

    # ─── 操作 ──────────────────────────────────────────────────

    def _toggle_edit(self):
        self.preview.setReadOnly(not self.edit_toggle_btn.isChecked())

    def _copy_to_clipboard(self):
        content = self.preview.toPlainText() if self.edit_toggle_btn.isChecked() else self.current_markdown
        if content:
            QApplication.clipboard().setText(content)
            self.status_label.setText('已复制到剪贴板 ✓')
            self.status_label.setStyleSheet(SUCCESS_COLOR)

    def _save_as(self):
        content = self.preview.toPlainText() if self.edit_toggle_btn.isChecked() else self.current_markdown
        if not content:
            return

        default_name = 'output.md'
        if self.current_file:
            base = os.path.splitext(os.path.basename(self.current_file))[0]
            default_name = f'{base}.md'

        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存 Markdown', default_name,
            'Markdown 文件 (*.md);;所有文件 (*.*)',
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_label.setText(f'已保存至 {os.path.basename(file_path)} ✓')
                self.status_label.setStyleSheet(SUCCESS_COLOR)
            except Exception as e:
                QMessageBox.critical(self, '保存失败', str(e))

    def _export_to_word(self):
        """将当前 Markdown 内容导出为 Word 文档。"""
        content = self.preview.toPlainText() if self.edit_toggle_btn.isChecked() else self.current_markdown
        if not content:
            return

        default_name = 'output.docx'
        if self.current_file:
            base = os.path.splitext(os.path.basename(self.current_file))[0]
            default_name = f'{base}.docx'

        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出为 Word', default_name,
            'Word 文档 (*.docx);;所有文件 (*.*)',
        )
        if not file_path:
            return

        try:
            converter = MdToDocxConverter()
            converter.convert_text(content, file_path, self.settings)
            self.status_label.setText(f'已导出至 {os.path.basename(file_path)} ✓')
            self.status_label.setStyleSheet(SUCCESS_COLOR)
        except Exception as e:
            QMessageBox.critical(self, '导出失败', str(e))

    # ─── 设置 ──────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(
            self,
            max_image_width=self.settings.get('max_image_width', 800),
            code_block_style=self.settings.get('code_block_style', 'fenced'),
        )
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self.settings.update(dlg.get_values())
