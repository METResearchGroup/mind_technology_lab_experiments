"""Load prompt markdown from this package."""


def load_prompt(relative_path: str) -> str:
    """Read one UTF-8 prompt file under this package.

    Parameters
    ----------
    relative_path
        Path relative to ``workflow/prompts``.

    Returns
    -------
    str
        File text.

    Raises
    ------
    NotImplementedError
        Scaffold stub. The prompt-text step fills the reader.
    """
    raise NotImplementedError(relative_path)
