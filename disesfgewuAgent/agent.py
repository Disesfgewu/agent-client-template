from disesfgewuAgent.llmRouter import llmRouter
from disesfgewuAgent.skillLoader import skillLoader


class AgentClient:
    def __init__(self, skillPath, contextWindowSize):
        self._router = llmRouter()
        # To template get config path and use skillPath as skillFolderPath
        self._skillLoader = skillLoader()
        self._contextWindowsSize = contextWindowSize
        self._contextWindowsToken = 0
        self._inputStrCache = ""
        self._inputFiles = []

        # TODO: Implement Map-Reduce / Refine pattern for long inputs
        # - Chunk input when exceeding maxInputToken
        # - Process chunks via router.connect()
        # - Merge/summarize responses
        pass

    def getInputTokenSize(self, inputStr):
        # To add contextWindowsToken and input str now then count the size
        pass

    def compress(self):
        # To auto compress the self._inputStrCache as format:
        """
        [Context Memory]
        .....
        """
        # Maybe in words tokens 30% of _contextWindowsSize
