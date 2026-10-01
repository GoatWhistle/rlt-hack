class EmbeddingClientError(Exception):
    pass


class RegistryDumpError(Exception):
    """Выгрузку реестра МСП нельзя прочитать: нет файла, повреждён архив или XML."""
