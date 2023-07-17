# Copyright 2019 Compassion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
import types
from odoo.tests.common import TransactionCase

server_model = "odoo.addons.base_report_to_printer.models.printing_server"


class TestPrintingPrinter(TransactionCase):
    def setUp(self):
        super().setUp()
        self.server = self.env["printing.server"].create({})
        self.ServerModel = self.env["printing.server"]
        self.printer = self.env["printing.printer"].create(
            {
                "name": "Printer",
                "server_id": self.server.id,
                "system_name": "Sys Name",
                "default": True,
                "status": "unknown",
                "status_message": "Msg",
                "model": "res.users",
                "location": "Location",
                "uri": "URI",
            }
        )
        self.duplex_option = self.env["printer.option.choice"].create(
            {
                "option_key": "KMDuplex",
                "option_value": "2Sided",
                "printer_id": self.printer.id,
            }
        )
        self.printer_vals = {
            "printer-info": "Info",
            "printer-make-and-model": "Make and Model",
            "printer-location": "location",
            "device-uri": "URI",
            "printer-uri-supported": "/" + self.printer.system_name,
        }

    def test_print_options__copies_options_from_report(self):
        mock_report = mock.Mock()
        mock_report.printer_options = [self.duplex_option]

        options = self.printer.print_options(report=mock_report)

        self.assertEqual(options["KMDuplex"], "2Sided")

    def test_print_options__without_option(self):
        mock_report = mock.Mock()
        mock_report.printer_options = []

        options = self.printer.print_options(report=mock_report)

        self.assertEqual(options, {})

    @mock.patch("%s.cups" % server_model)
    def test_prepare_update_from_cups__load_options(self, patched_cups):
        patched_cups.Connection.return_value.getPPD3.return_value = (200, 1, None)
        self._mock_cups_options(self.printer, [])

        self.printer._prepare_update_from_cups(
            patched_cups.Connection(), self.printer_vals
        )

        self.assertEqual(len(self.printer.printer_options), 1)
        self.assertEqual(self.printer.printer_options[0].option_key, "KMDuplex")

    @mock.patch("%s.cups" % server_model)
    def test_prepare_update_from_cups(self, patched_cups):
        patched_cups.Connection.return_value.getPPD3.return_value = (200, 1, None)
        self._mock_cups_options(
            self.printer, [{"choice": "2Sided"}, {"choice": "1Sided"}]
        )

        vals = self.printer._prepare_update_from_cups(
            patched_cups.Connection(), self.printer_vals
        )

        # OutputBin:bin1 was already inserted
        self.assertEqual(len(vals["printer_option_choices"]), 1)
        self.assertIn(
            (0, 0, {"option_key": "KMDuplex", "option_value": "1Sided"}),
            vals["printer_option_choices"],
        )
        self.assertNotIn(
            (0, 0, {"option_key": "KMDuplex", "option_value": "2Sided"}),
            vals["printer_option_choices"],
        )

    def _mock_cups_options(self, printer, choices):
        def mock__get_cups_ppd(*args):
            mock_ppd = mock.Mock()
            # Mock optionGroups
            mock_option_group = mock.Mock()
            mock_option = mock.Mock()
            mock_option.keyword = "KMDuplex"
            mock_option.choices = choices
            mock_option_group.options = [mock_option]
            mock_ppd.optionGroups = [mock_option_group]
            # Mock findOption
            mock_ppd.findOption = lambda x: mock_option
            return "pdd_path", mock_ppd

        printer._get_cups_ppd = types.MethodType(mock__get_cups_ppd, self.printer)
