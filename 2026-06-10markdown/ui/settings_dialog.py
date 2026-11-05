"""设置对话框。"""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
    QCheckBox,
)


class SettingsDialog(QDialog):
    """转换选项设置对话框。"""

    def __init__(self, parent=None, max_image_width: int = 800, code_block_style: str = 'fenced'):
        super().__init__(parent)
        self.setWindowTitle('设置')
        self.setMinimumWidth(350)
        self._setup_ui(max_image_width, code_block_style)

    def _setup_ui(self, max_image_width: int, code_block_style: str):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.image_width_spin = QSpinBox()
        self.image_width_spin.setRange(200, 2000)
        self.image_width_spin.setValue(max_image_width)
        self.image_width_spin.setSuffix(' px')
        self.image_width_spin.setSingleStep(50)
        form.addRow('图片最大宽度：', self.image_width_spin)

        style_layout = QHBoxLayout()
        self.fenced_check = QCheckBox('围栏式 (```)')
        self.fenced_check.setChecked(code_block_style == 'fenced')
        style_layout.addWidget(self.fenced_check)
        form.addRow('代码块样式：', style_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            'max_image_width': self.image_width_spin.value(),
            'code_block_style': 'fenced' if self.fenced_check.isChecked() else 'indented',
        }
