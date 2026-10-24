import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.tests.test_fraud import TestFraudAgent
from wire_check.tests.test_entity import TestEntityAgent
from wire_check.tests.test_sanctions import TestSanctionsAgent
from wire_check.tests.test_decision import TestDecisionEngine
from wire_check.tests.test_orchestrator import TestOrchestratorWorkflow
from wire_check.tests.test_cards import TestInteractiveCards

if __name__ == '__main__':
    unittest.main()
