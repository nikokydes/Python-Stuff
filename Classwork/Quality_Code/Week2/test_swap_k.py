import a1
import unittest


class TestSwapK(unittest.TestCase):
    """ Test class for function a1.swap_k. """

    def test_general_case(self):
        """
        Test swap_k for a general list with more than
        4 elements
        """

        list1          = [1, 2, 3, 4, 5, 6]
        list1_expected = [5, 6, 3, 4, 1, 2]
        
        a1.swap_k(list1,2)
        
        self.assertEqual(list1, list1_expected)


if __name__ == '__main__':
    unittest.main(exit=False)
