class SkillsheetError(Exception):
    """利用者に理由を示して終了すべきエラー（CLI が標準エラーに出し、終了コード 1 にする）。"""
