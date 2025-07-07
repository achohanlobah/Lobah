# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import api, fields, models


class AccountGroup(models.Model):
    _inherit = "account.group"

    """
        complete_code and complete_code does not used anywhere 
        but in old module it is there 
    """
    complete_name = fields.Char("Full Name", compute="_compute_complete_name", recursive=True)
    complete_code = fields.Char("Full Code", compute="_compute_complete_code",recursive=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        """ Forms complete name of location from parent location to child location. """
        if self.parent_id.complete_name:
            self.complete_name = "{}/{}".format(self.parent_id.complete_name, self.name)
        else:
            self.complete_name = self.name

    @api.depends("code_prefix_start", "parent_id.complete_code")
    def _compute_complete_code(self):
        """ Forms complete code of location from parent location to child location. """
        if self.parent_id.complete_code:
            self.complete_code = "{}/{}".format(
                self.parent_id.complete_code, self.code_prefix_start
            )
        else:
            self.complete_code = self.code_prefix_start
