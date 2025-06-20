from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from datetime import datetime
import xlwt
import io
import datetime
from datetime import timedelta
from datetime import date
from odoo.tools.float_utils import float_round
from dateutil.relativedelta import relativedelta

class BalanceSheetReport(models.TransientModel):
    _name = 'balance.sheet.custom.report'
    _description = "Balance Sheet Cutom Report"


    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    account_ids = fields.Many2many('account.account', string='Accounts')
    account_income_percentage = fields.Boolean(string= 'Show Income Percentage', default=False)
    income_percentage = fields.Selection([('repeatnone','Repeat None'),('repeattag','Repeat Tag Wise')], string='income percentage', default='repeatnone')
    dimension_wise_project = fields.Selection([('none','None'),('month','Month Wise'),('year','Year Wise')],
                                              string='Dimension',
                                              default='none')
    projectwise = fields.Selection([('project', 'Project')],string='Project',default='project')
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')

    @api.model
    def default_get(self, fields):
        vals = super(BalanceSheetReport, self).default_get(fields)
        ac_ids = self.env['account.account'].search([])
        analytic_ids = self.env['account.analytic.account'].search([])
        self.env.cr.execute('update account_account set temp_accounts=False')
        self.env.cr.execute('update account_analytic_account set temp_analytics=False')
        if 'account_ids' in fields and not vals.get('account_ids') and ac_ids:
            iids = []
            for ac_id in ac_ids:
                iids.append(ac_id.id)
            vals['account_ids'] = [(6, 0, iids)]
        if 'analytic_account_ids' in fields and not vals.get('analytic_account_ids') and analytic_ids:
            aniids = []
            for ana_ac in analytic_ids:
                aniids.append(ana_ac.id)
            vals['analytic_account_ids'] = [(6, 0, aniids)]
        return vals

    def print_report_balance_sheet(self):
        if self.date_from >= self.date_to:
            raise UserError(_("Start Date is greater than or equal to End Date."))
        datas = {'form': self.read()[0],
                 'get_balance_sheet': self.get_balance_sheet_detial()
            }
        return self.env.ref('account_balance_sheet.action_report_balance_sheet').report_action([], data=datas)

    def get_balance_sheet_detial(self):

        CompanyImage = self.env.company.logo
        dateFrom = self.date_from
        dateTo = self.date_to
        MoveLineIds = []
        Vals = {}
        mainDict = []
        allData = []
        Initial_balance = []
        AllAccounts = self.account_ids
        FilteredAccountIds = AllAccounts.filtered(lambda a: a.temp_accounts)
        AccountIds = FilteredAccountIds.ids
        if not AccountIds:
            AccountIds = AllAccounts.ids
        AllAnalyticAccounts = self.analytic_account_ids
        FilteredAnalyticAccountIds = AllAnalyticAccounts.filtered(lambda a: a.temp_analytics)
        AnalyticAccountIds = FilteredAnalyticAccountIds
        if not AnalyticAccountIds:
            AnalyticAccountIds = AllAnalyticAccounts
        Status = ['posted']
        Projectwise = self.dimension_wise_project
        initial_date = dateFrom - timedelta(days=1)
        EarningLineIds = []
        earningsDict = []
        year = dateTo.strftime("%Y")
        earningfromdt = dict(year=int(year), month=1, day=1,)
        fromearningdate = datetime.datetime(**earningfromdt)
        earningdatefrom = fromearningdate.strftime("%Y-%m-%d")
        previousyear = dateTo - relativedelta(years=1)
        previousfromdt = dict(year=int(previousyear.strftime("%Y")), month=1, day=1,)
        previousfromdates = datetime.datetime(**previousfromdt)
        previousfromdate = previousfromdates.strftime("%Y-%m-%d")
        previoustodt = dict(year=int(previousyear.strftime("%Y")), month=12, day=31,)
        previoustodates = datetime.datetime(**previoustodt)
        previoustodate = previoustodates.strftime("%Y-%m-%d")
        
        netpreviousyearincome = 0.0
        previousyearincome = 0.0
        previousyearcost = 0.0
        previousyearexpenses = 0.0
        previousyearotherincome = 0.0
        previousyeardepriciation = 0.0
        netpreviousyearexpenses = 0.0
        netpreviousyear = 0.0
        netcurrentyear = 0.0
        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            self.env.cr.execute("""
                SELECT aml.date as date,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       a.account_type as acc_type,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                WHERE (aml.date >= %s) AND
                    (aml.date <= %s) AND
                    (aml.account_id in %s) AND
                    (am.state in %s) ORDER BY aml.date""",
                (str(earningdatefrom) + ' 00:00:00', str(dateTo) + ' 23:59:59', tuple([Account.id]), tuple(Status),))

            EarningLineIds = self.env.cr.fetchall()
            if EarningLineIds:
                for er in EarningLineIds:
                    date = er[0]
                    acount_debit = er[1]
                    account_credit = er[2]
                    account_code = er[3]
                    account_name = er[4]
                    account_type = er[5]
                    analytic_account_id = er[6]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_code': account_code,
                            'account_name': account_name,
                            'balance': Balance or 0.0,
                            'percentage': 0.0,
                            'account_type': account_type,
                            'account_debit': acount_debit,
                            'account_credit': account_credit,
                            'analytic_account_id': analytic_account_id,
                            'date': date,
                            }
                    earningsDict.append(Vals)

        for i in range(len(earningsDict)):

            if earningsDict[i]['account_type'] in ["Income", "income"] :
                previousyearincome += earningsDict[i]['balance']

            if earningsDict[i]['account_type'] in ["Cost of Revenue", "expense_direct_cost"]:
                previousyearcost += earningsDict[i]['balance']
                
            if earningsDict[i]['account_type'] in ["Other Income", "income_other"] :
                previousyearotherincome += earningsDict[i]['balance']
                
            if earningsDict[i]['account_type'] in ["Expenses", "expense"] :
                previousyearexpenses += earningsDict[i]['balance']

            if earningsDict[i]['account_type'] in ["Depreciation", "expense_depreciation"]:
                previousyeardepriciation += earningsDict[i]['balance']

        netpreviousyearincome = (abs(previousyearincome) - previousyearcost) + abs(previousyearotherincome)

        netpreviousyearexpenses = previousyearexpenses + previousyeardepriciation

        netcurrentyear = netpreviousyearincome - netpreviousyearexpenses

        if netcurrentyear == 0.0:
            for Account in self.env['account.account'].browse(AccountIds):
                Balance = 0.0
                self.env.cr.execute("""
                    SELECT aml.date as date,
                           aml.debit as debit,
                           aml.credit as credit,
                           a.code as code,
                           a.name->>'en_US' as acc_name,
                           a.account_type as acc_type,
                           aa.name->>'en_US' as analytic,
                           aml.id as movelineid
                    FROM account_move_line aml
                    LEFT JOIN account_move am ON (am.id=aml.move_id)
                    LEFT JOIN LATERAL (
                        SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                        FROM jsonb_each_text(aml.analytic_distribution)
                    ) ak ON true
                    LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                    LEFT JOIN account_account a ON (a.id=aml.account_id)
                    WHERE (aml.date >= %s) AND
                        (aml.date <= %s) AND
                        (aml.account_id in %s) AND
                        (am.state in %s) ORDER BY aml.date""",
                                    (str(previousfromdate) + ' 00:00:00', str(previoustodate) + ' 23:59:59', tuple([Account.id]), tuple(Status),))
                EarningLineIds = self.env.cr.fetchall()
                if EarningLineIds:
                    for er in EarningLineIds:
                        date = er[0]
                        acount_debit = er[1]
                        account_credit = er[2]
                        account_code = er[3]
                        account_name = er[4]
                        account_type = er[5]
                        analytic_account_id = er[6]
                        Balance = 0.0
                        Balance = Balance + (acount_debit - account_credit)
                        Vals = {'account_code':account_code,
                                'account_name':account_name,
                                'balance': Balance or 0.0,
                                'percentage': 0.0,
                                'account_type':account_type,
                                'account_debit':acount_debit,
                                'account_credit':account_credit,
                                'analytic_account_id':analytic_account_id,
                                'date':date,
                                }
                        earningsDict.append(Vals)

            for i in range(len(earningsDict)):

                if earningsDict[i]['account_type'] in ["Income", "income"] :
                    previousyearincome += earningsDict[i]['balance']

                if earningsDict[i]['account_type'] in ["Cost of Revenue", "expense_direct_cost"]:
                    previousyearcost += earningsDict[i]['balance']

                if earningsDict[i]['account_type'] in ["Other Income", "income_other"] :
                    previousyearotherincome += earningsDict[i]['balance']

                if earningsDict[i]['account_type'] in ["Expenses", "expense"] :
                    previousyearexpenses += earningsDict[i]['balance']

                if earningsDict[i]['account_type'] in ["Depreciation", "expense_depreciation"]:
                    previousyeardepriciation += earningsDict[i]['balance']

            netpreviousyearincome = (abs(previousyearincome) - previousyearcost) + abs(previousyearotherincome)

            netpreviousyearexpenses = previousyearexpenses + previousyeardepriciation

            netpreviousyear = netpreviousyearincome - netpreviousyearexpenses

        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            self.env.cr.execute("""
                SELECT aml.account_id as account_id,
                       aml.date as date,
                       a.account_type as acc_type,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                WHERE (aml.date <= %s) AND
                      (aml.account_id in %s) And
                      (am.state in %s) ORDER BY aml.account_id""",
                                (str(dateTo) + ' 00:00:00', tuple([Account.id]), tuple(Status),))

            MoveLineIds = self.env.cr.fetchall()

            if MoveLineIds:
                for ml in MoveLineIds:
                    account_id = ml[0]
                    account_date = ml[1]
                    account_type = ml[2]
                    account_debit = ml[3]
                    account_credit = ml[4]
                    account_code = ml[5]
                    account_name = ml[6]
                    anlaytic_name = ml[7]
                    balance = 0.0
                    balance = balance + (account_debit - account_credit)
                    Vals = {'account_id':account_id,
                            'account_type':account_type,
                            'account_date':account_date,
                            'account_debit':account_debit,
                            'account_credit':account_credit,
                            'account_code': account_code,
                            'account_name': account_name,
                            'analytic_account':anlaytic_name,
                            'balance': balance,

                            }
                    allData.append(Vals)

            self.env.cr.execute("""
                SELECT aml.account_id as account_id,
                       max(aml.date) as date,
                       sum(aml.debit) as debit,
                       sum(aml.credit) as credit
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                WHERE (aml.date <= %s) AND
                      (aml.account_id in %s) And
                      (am.state in %s) Group BY aml.account_id""",
                                (str(dateTo) + ' 00:00:00', tuple([Account.id]), tuple(Status),))

            Initial_balance = self.env.cr.fetchall()

            if Initial_balance:
                for ml in Initial_balance:
                    account_id = ml[0]
                    account_date = ml[1]
                    acount_debit = ml[2]
                    account_credit = ml[3]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_id':account_id,
                            'account_date':account_date,
                            'account_debit':acount_debit,
                            'account_credit':account_credit,
                            'balance': Balance,
                            }
                    mainDict.append(Vals)

        for j in range(len(mainDict)):
            for i in range(len(allData)):
                if allData[i]['account_id'] == mainDict[j]['account_id']:
                    mainDict[j]['account_code'] =  allData[i]['account_code']
                    mainDict[j]['account_name'] =  allData[i]['account_name']
                    mainDict[j]['account_type'] =  allData[i]['account_type']

                    
        allocated_balance = 0.0
        for j in range(len(mainDict)):
            if mainDict[j]['account_type'] in ["Current Year Earnings", "equity_unaffected"]:
                allocated_balance = mainDict[j]['balance']
                mainDict[j]['account_name'] = 'Current Year Earnings'
                if netpreviousyear :
                    mainDict[j]['balance'] =  0.0
                else:    
                    mainDict[j]['balance'] =  netcurrentyear
                    
                if dateTo.strftime("%Y") == mainDict[j]['account_date'].strftime("%Y"):
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance':allocated_balance , 'account_code': ' ','account_name': 'Current Year Allocated Earnings', 'account_type': mainDict[j]['account_type'],})
                else:
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance':0.0 , 'account_code': ' ','account_name': 'Current Year Allocated Earnings', 'account_type': mainDict[j]['account_type']})

                if netpreviousyear:
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance': netpreviousyear, 'account_code': ' ','account_name': 'Previous Year', 'account_type':'previous year',})
                else:
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance':0.0 , 'account_code': ' ','account_name': 'Previous Year', 'account_type':'previous year',})

        return mainDict


    def month_year_wise(self):

        CompanyImage = self.env.company.logo
        dateFrom = self.date_from
        dateTo = self.date_to
        MoveLineIds = []
        Vals = {}
        mainDict = []
        allData = []
        Initial_balance = []
        EarningLineIds = []
        Status = ['posted']
        AllAccounts = self.account_ids
        FilteredAccountIds = AllAccounts.filtered(lambda a: a.temp_accounts)
        AccountIds = FilteredAccountIds.ids
        if not AccountIds:
            AccountIds = AllAccounts.ids
        AllAnalyticAccounts = self.analytic_account_ids
        FilteredAnalyticAccountIds = AllAnalyticAccounts.filtered(lambda a: a.temp_analytics)
        AnalyticAccountIds = FilteredAnalyticAccountIds
        if not AnalyticAccountIds:
            AnalyticAccountIds = AllAnalyticAccounts
        AnalyticAccountId = [i.id for i in AnalyticAccountIds]
        EarningLineIds = []
        earningsDict = []
        year = dateTo.strftime("%Y")
        earningfromdt = dict(year=int(year), month=1, day=1,)
        fromearningdate = datetime.datetime(**earningfromdt)
        earningdatefrom = fromearningdate.strftime("%Y-%m-%d")
        previousyear = dateTo - relativedelta(years=1)
        previousfromdt = dict(year=int(previousyear.strftime("%Y")), month=1, day=1,)
        previousfromdates = datetime.datetime(**previousfromdt)
        previousfromdate = previousfromdates.date()
        previoustodt = dict(year=int(previousyear.strftime("%Y")), month=12, day=31,)
        previoustodates = datetime.datetime(**previoustodt)
        previoustodate = previoustodates.date()

        netbalance_list = []
        third_income_lists = []
        third_expense_lists = []
        totalincomecolumn = [] 
        thirdincomelists = []
        totalcostcolumn = [] 
        thirdcostlists = [] 
        totalothercolumn = [] 
        thirdotherlists = [] 
        totalexpensecolumn = [] 
        thirdexpenselists = [] 
        totaldepriciationcolumn = [] 
        thirddepriciationlists = [] 
        finalgross_list =[] 
        finalincome_list = [] 
        finalexpense_list =[]

        cur_date = previousfromdate
        end = previoustodate
        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            self.env.cr.execute("""
                SELECT aml.date as date,
                       aml.debit as debit,
                       aml.credit as credit,
                       aml.account_id as account_id,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       a.account_type as acc_type,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                WHERE (aml.date >= %s) AND
                    (aml.date <= %s) AND
                    (aml.account_id in %s) AND
                    (am.state in %s) ORDER BY aml.date""",
                (str(earningdatefrom) + ' 00:00:00', str(dateTo) + ' 23:59:59', tuple([Account.id]), tuple(Status),))

            EarningLineIds = self.env.cr.fetchall()
            if EarningLineIds:
                for er in EarningLineIds:
                    date = er[0]
                    acount_debit = er[1]
                    account_credit = er[2]
                    account_id = er[3]
                    account_code = er[4]
                    account_name = er[5]
                    account_type = er[6]
                    analytic_account_id = er[7]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_id' : account_id,
                            'account_code':account_code,
                            'account_name':account_name,
                            'balance': Balance or 0.0,
                            'percentage': 0.0,
                            'account_type':account_type,
                            'account_debit':acount_debit,
                            'account_credit':account_credit,
                            'analytic_account_id':analytic_account_id,
                            'account_date':date,
                            }
                    earningsDict.append(Vals)

        if not earningsDict:
            cur_date = previousfromdate
            end = previoustodate
            for Account in self.env['account.account'].browse(AccountIds):
                Balance = 0.0
                self.env.cr.execute("""
                    SELECT aml.date as date,
                           aml.debit as debit,
                           aml.credit as credit,
                           aml.account_id as account_id,
                           a.code as code,
                           a.name->>'en_US' as acc_name,
                           a.account_type as acc_type,
                           aa.name->>'en_US' as analytic,
                           aml.id as movelineid
                    FROM account_move_line aml
                    LEFT JOIN account_move am ON (am.id=aml.move_id)
                    LEFT JOIN LATERAL (
                        SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                        FROM jsonb_each_text(aml.analytic_distribution)
                    ) ak ON true
                    LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                    LEFT JOIN account_account a ON (a.id=aml.account_id)
                    WHERE (aml.date >= %s) AND
                        (aml.date <= %s) AND
                        (aml.account_id in %s) AND
                        (am.state in %s) ORDER BY aml.date""",
                    (str(previousfromdate) + ' 00:00:00', str(previoustodate) + ' 23:59:59', tuple([Account.id]), tuple(Status),))
                EarningLineIds = self.env.cr.fetchall()

                if EarningLineIds:
                    for er in EarningLineIds:
                        date = er[0]
                        acount_debit = er[1]
                        account_credit = er[2]
                        account_id = er[3]
                        account_code = er[4]
                        account_name = er[5]
                        account_type = er[6]
                        analytic_account_id = er[7]
                        Balance = 0.0
                        Balance = Balance + (acount_debit - account_credit)
                        Vals = {'account_id' : account_id,
                                'account_code':account_code,
                                'account_name':account_name,
                                'balance': Balance or 0.0,
                                'percentage': 0.0,
                                'account_type':account_type,
                                'account_debit':acount_debit,
                                'account_credit':account_credit,
                                'analytic_account_id':analytic_account_id,
                                'account_date':date,
                                }
                        earningsDict.append(Vals)

        analytic_account_list = []
        analytic_main_list = []
        analytic_first_list = []
        analytic_news_list = []
        analytic_second_list = []
        if self.dimension_wise_project == 'month':
            for i in range(0,len(earningsDict)):
                if (earningsDict[i]['account_id'],earningsDict[i]['account_date'].strftime("%b %y")) not in analytic_account_list:
                    analytic_main_list.append({
                                      'account_id': earningsDict[i]['account_id'],
                                      'account_name':earningsDict[i]['account_name'],
                                      'debit': earningsDict[i]['account_debit'],
                                      'credit': earningsDict[i]['account_credit'],
                                      'balance': earningsDict[i]['account_debit'] - earningsDict[i]['account_credit'] or 00.00,
                                      'account_type':earningsDict[i]['account_type'],
                                      'month': earningsDict[i]['account_date'].strftime("%b %y")
                                      })
                    analytic_account_list.append((earningsDict[i]['account_id'],earningsDict[i]['account_date'].strftime("%b %y")))
                else:
                    analytic_first_list.append({
                                      'account_id': earningsDict[i]['account_id'],
                                      'account_name':earningsDict[i]['account_name'],
                                      'debit': earningsDict[i]['account_debit'],
                                      'credit': earningsDict[i]['account_credit'],
                                      'balance': earningsDict[i]['account_debit'] - earningsDict[i]['account_credit'] or 00.00,
                                      'account_type':earningsDict[i]['account_type'],
                                      'month': earningsDict[i]['account_date'].strftime("%b %y")
                                      })
            if earningsDict:
                for j in range(0,len(analytic_main_list)):
                    for k in range(0,len(analytic_first_list)):
                        if analytic_first_list[k]['account_id'] == analytic_main_list[j]['account_id'] and analytic_first_list[k]['month'] == analytic_main_list[j]['month']:
                            analytic_main_list[j]['debit'] =  analytic_main_list[j]['debit'] + analytic_first_list[k]['debit']
                            analytic_main_list[j]['credit'] = analytic_main_list[j]['credit'] + analytic_first_list[k]['credit']
                            analytic_main_list[j]['balance'] = analytic_main_list[j]['debit'] - analytic_main_list[j]['credit']

            fetch_monthwise_data = []
            column1 = []
            listd = ''
            first_Column_values = earningsDict[0]
            for i in range(len(earningsDict)):
                if i == 0:
                    listd = earningsDict[i]['account_date'].strftime("%Y")

            a = dict(year=int(listd), month=1, day=1,)
            dt = datetime.datetime(**a).date()
            enddate = dict(year=int(listd), month=12, day=31,)
            enddt = datetime.datetime(**enddate).date()
            cur_date = dt
            end = enddt
            while cur_date < end:
                cur_date_strf = str(cur_date.strftime('%b %y') or '')
                cur_date += relativedelta(months=1)
                fetch_monthwise_data.append(cur_date_strf)

            for i in range(0,len(analytic_main_list)):
                if analytic_main_list[i]['account_id'] not in analytic_second_list:
                    analytic_news_list.append(analytic_main_list[i])
                    analytic_second_list.append(analytic_main_list[i]['account_id'])

            for j in range(0,len(analytic_news_list)):
                for k in range(0,len(analytic_main_list)):
                    if analytic_news_list[j]['account_id'] == analytic_main_list[k]['account_id']:
                        column1.append({analytic_main_list[k]['month']:analytic_main_list[k]['balance']})
                        a1 = [(list(c.keys())[0]) for c in column1]
                        res = column1 + [{i:000.0} for i in fetch_monthwise_data if i not in a1]
                        res2 = sorted(res, key = lambda ele: fetch_monthwise_data.index(list(ele.keys())[0]))
                        analytic_news_list[j]['columns'] = res2
                        analytic_news_list[j]['caret_options'] = 'account.account'
                        
                    else:
                       column1.clear()

        if self.dimension_wise_project == 'year':
            for i in range(0,len(earningsDict)):
                if (earningsDict[i]['account_id'],earningsDict[i]['account_date'].strftime("%Y")) not in analytic_account_list:
                        analytic_main_list.append({
                                          'account_id': earningsDict[i]['account_id'],
                                          'account_name':earningsDict[i]['account_name'],
                                          'debit': earningsDict[i]['account_debit'],
                                          'credit': earningsDict[i]['account_credit'],
                                          'balance': earningsDict[i]['account_debit'] - earningsDict[i]['account_credit'] or 00.00,
                                          'account_type':earningsDict[i]['account_type'],
                                          'year': earningsDict[i]['account_date'].strftime("%Y")
                                          })
                        analytic_account_list.append((earningsDict[i]['account_id'],earningsDict[i]['account_date'].strftime("%Y")))        
                else:
                    analytic_first_list.append({
                                      'account_id': earningsDict[i]['account_id'],
                                      'account_name':earningsDict[i]['account_name'],
                                      'debit': earningsDict[i]['account_debit'],
                                      'credit': earningsDict[i]['account_credit'],
                                      'balance': earningsDict[i]['account_debit'] - earningsDict[i]['account_credit'] or 00.00,
                                      'account_type':earningsDict[i]['account_type'],
                                      'year': earningsDict[i]['account_date'].strftime("%Y")
                                      })
            if earningsDict:
                for j in range(0,len(analytic_main_list)):
                    for k in range(0,len(analytic_first_list)):
                        if analytic_first_list[k]['account_id'] == analytic_main_list[j]['account_id'] and analytic_first_list[k]['year'] == analytic_main_list[j]['year']:
                            analytic_main_list[j]['debit'] =  analytic_main_list[j]['debit'] + analytic_first_list[k]['debit']
                            analytic_main_list[j]['credit'] = analytic_main_list[j]['credit'] + analytic_first_list[k]['credit']
                            analytic_main_list[j]['balance'] = analytic_main_list[j]['debit'] - analytic_main_list[j]['credit']

        
            a1 = ''
            res2 =''
            fetch_yearwise_data = []
            analytic_news_list = []
            analytic_second_list = []
            column1 = []
            listd = ''
            for i in range(len(earningsDict)):
                if i == 0:
                    listd = earningsDict[i]['account_date'].strftime("%Y")
            a = dict(year=int(listd), month=1, day=1,)
            dt = datetime.datetime(**a).date()
            enddate = dict(year=int(listd), month=12, day=31,)
            enddt = datetime.datetime(**enddate).date()
            cur_date = dt
            end = enddt
            while cur_date <= end:
                cur_date_strf = str(cur_date.strftime('%Y') or '')
                cur_date += relativedelta(years=1)
                fetch_yearwise_data.append(cur_date_strf)

            for i in range(0,len(analytic_main_list)):
                if analytic_main_list[i]['account_id'] not in analytic_second_list:
                    analytic_news_list.append(analytic_main_list[i])
                    analytic_second_list.append(analytic_main_list[i]['account_id'])

            for j in range(0,len(analytic_news_list)):
                for k in range(0,len(analytic_main_list)):
                    if analytic_news_list[j]['account_id'] == analytic_main_list[k]['account_id']:
                        column1.append({analytic_main_list[k]['year']:analytic_main_list[k]['balance']})
                        a1 = [(list(c.keys())[0]) for c in column1]
                        res = column1 + [{i:000.0} for i in fetch_yearwise_data if i not in a1]
                        res2 = sorted(res, key = lambda ele: fetch_yearwise_data.index(list(ele.keys())[0]))
                        # res2  = sorted(res, key=lambda d: sorted(d.items()))
                        analytic_news_list[j]['columns'] = res2
                        analytic_news_list[j]['caret_options'] = 'account.account'
                        
                    else:
                       column1.clear()
        
        if self.dimension_wise_project == 'year' or self.dimension_wise_project == 'month' :

            for s in range(0,len(analytic_news_list)):
                if analytic_news_list[s]['account_type'] in ["Income", "income"] :
                    totalincomecolumn = analytic_news_list[s]['columns']
                    listd = [list(c.values())[0] for c in totalincomecolumn]
                    thirdincomelists.append(listd)

                if analytic_news_list[s]['account_type'] in ["Cost of Revenue", "expense_direct_cost"]:
                    totalcostcolumn = analytic_news_list[s]['columns']
                    listd = [list(c.values())[0] for c in totalcostcolumn]
                    thirdcostlists.append(listd)

                if analytic_news_list[s]['account_type'] in ["Other Income", "income_other"] :
                    totalothercolumn = analytic_news_list[s]['columns']
                    listd = [list(c.values())[0] for c in totalothercolumn]
                    thirdotherlists.append(listd)

                if analytic_news_list[s]['account_type'] in ["Expenses", "expense"] :
                    totalexpensecolumn = analytic_news_list[s]['columns']
                    listd = [list(c.values())[0] for c in totalexpensecolumn]
                    thirdexpenselists.append(listd)

                if analytic_news_list[s]['account_type'] in ["Depreciation", "expense_depreciation"]:
                    totaldepriciationcolumn = analytic_news_list[s]['columns']
                    listd = [list(c.values())[0] for c in totaldepriciationcolumn]
                    thirddepriciationlists.append(listd)

            thirdincomelist = [sum(i) for i in zip(*thirdincomelists)]
            thirdcostlist = [sum(i) for i in zip(*thirdcostlists)]
            thirdotherlist = [sum(i) for i in zip(*thirdotherlists)]
            thirdexpenselist = [sum(i) for i in zip(*thirdexpenselists)]
            thirddepriciationlist = [sum(i) for i in zip(*thirddepriciationlists)]

            for i in range(0, len(thirdincomelist)):
                if thirdincomelist and thirdcostlist:
                    finalgross_list.append(thirdincomelist[i] - thirdcostlist[i])
                elif thirdincomelist:
                    finalgross_list.append(thirdincomelist[i])
                elif thirdcostlist:
                    finalgross_list.append(thirdincomelist[i])

            for i in range(0,len(finalgross_list)):
                if finalgross_list and thirdotherlist:
                    finalincome_list.append(finalgross_list[i] + thirdotherlist[i])
                elif finalgross_list:
                    finalincome_list.append(finalgross_list[i])
                elif thirdotherlist:
                    finalincome_list.append(thirdotherlist[i])

            for i in range(0, len(thirdexpenselist)):
                if thirdexpenselist and thirddepriciationlist:
                    finalexpense_list.append(thirdexpenselist[i] - thirddepriciationlist[i])
                elif thirdexpenselist:
                    finalexpense_list.append(thirdexpenselist[i])
                elif thirddepriciationlist:
                    finalexpense_list.append(thirddepriciationlist[i])
                    
            for i in range(0, len(finalincome_list)): 
                netbalance_list.append(finalincome_list[i] + finalexpense_list[i])

        total_balance_list = {}

        if self.dimension_wise_project == 'year':
            total_balance_list = dict(zip(fetch_yearwise_data, netbalance_list))
        elif self.dimension_wise_project == 'month':
            total_balance_list = dict(zip(fetch_monthwise_data, netbalance_list))

        finalbalancedict = [{k:v} for k,v in total_balance_list.items()]

        for Account in self.env['account.account'].browse(AccountIds):
            self.env.cr.execute("""
                SELECT aml.account_id as account_id,
                       aml.date as date,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       a.account_type as acc_type,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                WHERE (aml.date <= %s) AND
                    (aml.account_id in %s) AND
                    (am.state in %s) ORDER BY aml.date""",
                (str(dateTo) + ' 00:00:00', tuple([Account.id]), tuple(Status),))
            MoveLineIds = self.env.cr.fetchall()

            if MoveLineIds:
                for ml in MoveLineIds:
                    account_id = ml[0]
                    account_date = ml[1]
                    account_debit = ml[2]
                    account_credit = ml[3]
                    account_code = ml[4]
                    account_name = ml[5]
                    account_type = ml[6]
                    anlaytic_name = ml[7]
                    balance = 0.0
                    balance = balance + (account_debit - account_credit)
                    Vals = {'account_id':account_id,
                            'account_type':account_type,
                            'account_date':account_date,
                            'account_debit':account_debit,
                            'account_credit':account_credit,
                            'account_code': account_code,
                            'account_name': account_name,
                            'analytic_account':anlaytic_name,
                            'balance': balance,

                            }
                    mainDict.append(Vals)

        account_list = []
        main_list = []
        first_list = []

        if self.dimension_wise_project == 'month':
            Fromdate =''
            for s in range(0,len(mainDict)):
                Fromdate = mainDict[0]['account_date']
            for i in range(0,len(mainDict)):
                if (mainDict[i]['account_id'],mainDict[i]['account_date'].strftime("%b %y")) not in account_list:
                    main_list.append({
                                      'account_id':mainDict[i]['account_id'],
                                      'account_name':mainDict[i]['account_name'],
                                      'debit': mainDict[i]['account_debit'],
                                      'credit': mainDict[i]['account_credit'],
                                      'balance': mainDict[i]['account_debit'] - mainDict[i]['account_credit'] or 00.00,
                                      'account_type':mainDict[i]['account_type'],
                                      'month': mainDict[i]['account_date'].strftime("%b %y")
                                      })
                    account_list.append((mainDict[i]['account_id'],mainDict[i]['account_date'].strftime("%b %y")))
                else:
                    first_list.append({
                                      'account_id':mainDict[i]['account_id'],
                                      'account_name':mainDict[i]['account_name'],
                                      'debit': mainDict[i]['account_debit'],
                                      'credit': mainDict[i]['account_credit'],
                                      'balance': mainDict[i]['account_debit'] - mainDict[i]['account_credit'] or 00.00,
                                      'account_type':mainDict[i]['account_type'],
                                      'month': mainDict[i]['account_date'].strftime("%b %y")
                                      })
            if mainDict:
                for j in range(0,len(main_list)):
                    for k in range(0,len(first_list)):
                        if first_list[k]['account_id'] == main_list[j]['account_id'] and first_list[k]['month'] == main_list[j]['month']:
                            main_list[j]['debit'] =  main_list[j]['debit'] + first_list[k]['debit']
                            main_list[j]['credit'] = main_list[j]['credit'] + first_list[k]['credit']
                            main_list[j]['balance'] = main_list[j]['debit'] - main_list[j]['credit']


            a1 = ''
            res2 =''
            fetch_monthwise_data = []
            news_list = []
            second_list = []
            column1 = []
            cur_date = Fromdate
            end = dateTo
            while cur_date < end:
                cur_date_strf = str(cur_date.strftime('%b %y') or '')
                cur_date += relativedelta(months=1)
                fetch_monthwise_data.append(cur_date_strf)

            for i in range(0,len(main_list)):
                if main_list[i]['account_id'] not in second_list:
                    news_list.append(main_list[i])
                    second_list.append(main_list[i]['account_id'])

            for j in range(0,len(news_list)):
                for k in range(0,len(main_list)):
                    if news_list[j]['account_id'] == main_list[k]['account_id']:
                        column1.append({main_list[k]['month']:main_list[k]['balance']})
                        a1 = [(list(c.keys())[0]) for c in column1]
                        res = column1 + [{i:000.0} for i in fetch_monthwise_data if i not in a1]
                        res2 = sorted(res, key = lambda ele: fetch_monthwise_data.index(list(ele.keys())[0]))
                        news_list[j]['columns'] = res2
                        news_list[j]['caret_options'] = 'account.account'
                        
                    else:
                       column1.clear()

        if self.dimension_wise_project == 'year':
            Fromdate =''
            for s in range(0,len(mainDict)):
                Fromdate = mainDict[0]['account_date']
            for i in range(len(mainDict)):
                if (mainDict[i]['account_id'],mainDict[i]['account_date'].strftime("%Y")) not in account_list:
                        main_list.append({
                                          'account_id':mainDict[i]['account_id'],
                                          'account_name':mainDict[i]['account_name'],
                                          'debit': mainDict[i]['account_debit'],
                                          'credit': mainDict[i]['account_credit'],
                                          'balance': mainDict[i]['account_debit'] - mainDict[i]['account_credit'] or 00.00,
                                          'account_type':mainDict[i]['account_type'],
                                          'year': mainDict[i]['account_date'].strftime("%Y")
                                          })
                        account_list.append((mainDict[i]['account_id'],mainDict[i]['account_date'].strftime("%Y")))        
                else:
                    first_list.append({
                                      'account_id':mainDict[i]['account_id'],
                                      'account_name':mainDict[i]['account_name'],
                                      'debit': mainDict[i]['account_debit'],
                                      'credit': mainDict[i]['account_credit'],
                                      'balance': mainDict[i]['account_debit'] - mainDict[i]['account_credit'] or 00.00,
                                      'account_type':mainDict[i]['account_type'],
                                      'year': mainDict[i]['account_date'].strftime("%Y")
                                      })
            if mainDict:
                for j in range(0,len(main_list)):
                    for k in range(0,len(first_list)):
                        if first_list[k]['account_id'] == main_list[j]['account_id'] and first_list[k]['year'] == main_list[j]['year']:
                            main_list[j]['debit'] =  main_list[j]['debit'] + first_list[k]['debit']
                            main_list[j]['credit'] = main_list[j]['credit'] + first_list[k]['credit']
                            main_list[j]['balance'] = main_list[j]['debit'] - main_list[j]['credit']

            a1 = ''
            res2 =''
            fetch_yearwise_data = []
            news_list = []
            second_list = []
            column1 = []

            cur_date = Fromdate
            end = dateTo
            while cur_date <= end:
                cur_date_strf = str(cur_date.strftime('%Y') or '')
                cur_date += relativedelta(years=1)
                fetch_yearwise_data.append(cur_date_strf)

            for i in range(0,len(main_list)):
                if main_list[i]['account_id'] not in second_list:
                    news_list.append(main_list[i])
                    second_list.append(main_list[i]['account_id'])

            for j in range(0,len(news_list)):
                for k in range(0,len(main_list)):
                    if news_list[j]['account_id'] == main_list[k]['account_id']:
                        column1.append({main_list[k]['year']:main_list[k]['balance']})
                        a1 = [(list(c.keys())[0]) for c in column1]
                        res = column1 + [{i:000.0} for i in fetch_yearwise_data if i not in a1]
                        res2 = sorted(res, key = lambda ele: fetch_yearwise_data.index(list(ele.keys())[0]))
                        news_list[j]['columns'] = res2
                        news_list[j]['caret_options'] = 'account.account'
                        
                    else:
                       column1.clear()

        
        return news_list,finalbalancedict

    def balance_sheet_excel(self):

        CompanyImage = self.env.company.logo
        dateFrom = self.date_from
        dateTo = self.date_to
        MoveLineIds = []
        Vals = {}
        mainDict = []
        allData = []
        Initial_balance = []
        AllAccounts = self.account_ids
        FilteredAccountIds = AllAccounts.filtered(lambda a: a.temp_accounts)
        AccountIds = FilteredAccountIds.ids
        if not AccountIds:
            AccountIds = AllAccounts.ids
        AllAnalyticAccounts = self.analytic_account_ids
        FilteredAnalyticAccountIds = AllAnalyticAccounts.filtered(lambda a: a.temp_analytics)
        AnalyticAccountIds = FilteredAnalyticAccountIds
        if not AnalyticAccountIds:
            AnalyticAccountIds = AllAnalyticAccounts
        Status = ['posted']
        Projectwise = self.dimension_wise_project
        initial_date = dateFrom - timedelta(days=1)
        EarningLineIds = []
        earningsDict = []
        year = dateTo.strftime("%Y")
        earningfromdt = dict(year=int(year), month=1, day=1,)
        fromearningdate = datetime.datetime(**earningfromdt)
        earningdatefrom = fromearningdate.strftime("%Y-%m-%d")
        previousyear = dateTo - relativedelta(years=1)
        previousfromdt = dict(year=int(previousyear.strftime("%Y")), month=1, day=1,)
        previousfromdates = datetime.datetime(**previousfromdt)
        previousfromdate = previousfromdates.strftime("%Y-%m-%d")
        previoustodt = dict(year=int(previousyear.strftime("%Y")), month=12, day=31,)
        previoustodates = datetime.datetime(**previoustodt)
        previoustodate = previoustodates.strftime("%Y-%m-%d")
        
        netpreviousyearincome = 0.0
        previousyearincome = 0.0
        previousyearcost = 0.0
        previousyearexpenses = 0.0
        previousyearotherincome = 0.0
        previousyeardepriciation = 0.0
        netpreviousyearexpenses = 0.0
        curryearincome = 0.0
        curryearcost = 0.0
        curryearotherincome = 0.0
        curryeardepriciation = 0.0
        curryearexpenses = 0.0
        netpreviousyear = 0.0
        netcurrentyear = 0.0
        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            self.env.cr.execute("""
                SELECT aml.date as date,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       a.account_type as acc_type,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                WHERE (aml.date >= %s) AND
                    (aml.date <= %s) AND
                    (aml.account_id in %s) AND
                    (am.state in %s) ORDER BY aml.date""",
                                (str(earningdatefrom) + ' 00:00:00', str(dateTo) + ' 23:59:59', tuple([Account.id]),
                                 tuple(Status),))
            EarningLineIds = self.env.cr.fetchall()
            if EarningLineIds:
                for er in EarningLineIds:
                    date = er[0]
                    acount_debit = er[1]
                    account_credit = er[2]
                    account_code = er[3]
                    account_name = er[4]
                    account_type = er[5]
                    analytic_account_id = er[6]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_code': account_code,
                            'account_name': account_name,
                            'balance': Balance or 0.0,
                            'percentage': 0.0,
                            'account_type': account_type,
                            'account_debit': acount_debit,
                            'account_credit': account_credit,
                            'analytic_account_id': analytic_account_id,
                            'date': date,
                            }
                    earningsDict.append(Vals)

        for i in range(len(earningsDict)):
            if earningsDict[i]['account_type'] in ["Income", "income"] :
                curryearincome += earningsDict[i]['balance']
            if earningsDict[i]['account_type'] in ["Cost of Revenue", "expense_direct_cost"]:
                curryearcost += earningsDict[i]['balance']
            if earningsDict[i]['account_type'] in ["Other Income", "income_other"] :
                curryearotherincome += earningsDict[i]['balance']
            if earningsDict[i]['account_type'] in ["Expenses", "expense"] :
                curryearexpenses += earningsDict[i]['balance']
            if earningsDict[i]['account_type'] in ["Depreciation", "expense_depreciation"]:
                curryeardepriciation += earningsDict[i]['balance']

        netcurryearincome = (abs(curryearincome) - curryearcost) + abs(curryearotherincome)

        netcurryearexpenses = curryearexpenses + curryeardepriciation

        netcurrentyear = netcurryearincome - netcurryearexpenses

        current_year_allocated_balance = 0.0
        current_year_allocated_move_lines = self.env['account.move.line'].search([('account_id','=','Undistributed Profit'),('date','=',dateTo)])
        if current_year_allocated_move_lines:
            current_year_allocated_balance = current_year_allocated_move_lines.debit - current_year_allocated_move_lines.credit
            if not current_year_allocated_balance:
                current_year_allocated_balance = 0.0
        
        # if netcurrentyear == 0.0:
        journal_entries = []
        previousearningsDict = []
        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            # Journal Entries
            self.env.cr.execute("""
                SELECT aml.date as date,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       a.account_type as acc_type,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                WHERE (aml.date >= %s) AND
                    (aml.date <= %s) AND
                    (aml.account_id in %s) AND
                    (am.state in %s) ORDER BY aml.date""",
                                (str(previousfromdate) + ' 00:00:00', str(previoustodate) + ' 23:59:59',
                                 tuple([Account.id]), tuple(Status),))
            journal_entries = self.env.cr.fetchall()

            if journal_entries:
                for er in journal_entries:
                    date = er[0]
                    acount_debit = er[1]
                    account_credit = er[2]
                    account_code = er[3]
                    account_name = er[4]
                    account_type = er[5]
                    analytic_account_id = er[6]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_code': account_code,
                            'account_name': account_name,
                            'balance': Balance or 0.0,
                            'percentage': 0.0,
                            'account_type': account_type,
                            'account_debit': acount_debit,
                            'account_credit': account_credit,
                            'analytic_account_id': analytic_account_id,
                            'date': date,
                            }
                    previousearningsDict.append(Vals)
        
        for i in range(len(previousearningsDict)):
            if previousearningsDict[i]['account_type'] in ["Income", "income"] :
                previousyearincome += previousearningsDict[i]['balance']

            if previousearningsDict[i]['account_type'] in ["Cost of Revenue", "expense_direct_cost"]:
                previousyearcost += previousearningsDict[i]['balance']
                
            if previousearningsDict[i]['account_type'] in ["Other Income", "income_other"] :
                previousyearotherincome += previousearningsDict[i]['balance']
                
            if previousearningsDict[i]['account_type'] in ["Expenses", "expense"] :
                previousyearexpenses += previousearningsDict[i]['balance']

            if previousearningsDict[i]['account_type'] in ["Depreciation", "expense_depreciation"] :
                previousyeardepriciation += previousearningsDict[i]['balance']
        
        netpreviousyearincome = (abs(previousyearincome) - previousyearcost) + abs(previousyearotherincome)

        netpreviousyearexpenses = previousyearexpenses + previousyeardepriciation

        netpreviousyear = netpreviousyearincome - netpreviousyearexpenses
        
        account_move_lines = self.env['account.move.line'].search([('account_id','=','Undistributed Profit'),('date','=',previoustodate)])
        if account_move_lines:
            move_line_balance = account_move_lines.debit - account_move_lines.credit
            if round((netpreviousyear),2) == move_line_balance:
                netpreviousyear = 0.0

        netunallocatedearning = netpreviousyear + netcurrentyear

        for Account in self.env['account.account'].browse(AccountIds):
            Balance = 0.0
            self.env.cr.execute("""
                SELECT aml.account_id as account_id,
                       aml.date as date,
                       a.account_type as acc_type,
                       aml.debit as debit,
                       aml.credit as credit,
                       a.code as code,
                       a.name->>'en_US' as acc_name,
                       aa.name->>'en_US' as analytic,
                       aml.id as movelineid
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                LEFT JOIN LATERAL (
                    SELECT (regexp_matches(jsonb_object_keys(aml.analytic_distribution), '\d+', 'g'))[1]::int as analytic_key
                    FROM jsonb_each_text(aml.analytic_distribution)
                ) ak ON true
                LEFT JOIN account_analytic_account aa ON ak.analytic_key = aa.id
                WHERE (aml.date <= %s) AND
                      (aml.account_id in %s) And
                      (am.state in %s) ORDER BY aml.account_id""",
                                (str(dateTo) + ' 00:00:00', tuple([Account.id]), tuple(Status),))

            MoveLineIds = self.env.cr.fetchall()
            if MoveLineIds:
                for ml in MoveLineIds:
                    account_id = ml[0]
                    account_date = ml[1]
                    account_type = ml[2]
                    account_debit = ml[3]
                    account_credit = ml[4]
                    account_code = ml[5]
                    account_name = ml[6]
                    anlaytic_name = ml[7]
                    balance = 0.0
                    balance = balance + (account_debit - account_credit)
                    Vals = {'account_id': account_id,
                            'account_type': account_type,
                            'account_date': account_date,
                            'account_debit': account_debit,
                            'account_credit': account_credit,
                            'account_code': account_code,
                            'account_name': account_name,
                            'analytic_account': anlaytic_name,
                            'balance': balance,

                            }
                    allData.append(Vals)

            self.env.cr.execute("""
                SELECT aml.account_id as account_id,
                       max(aml.date) as date,
                       sum(aml.debit) as debit,
                       sum(aml.credit) as credit
                FROM account_move_line aml
                LEFT JOIN account_move am ON (am.id=aml.move_id)
                LEFT JOIN account_account a ON (a.id=aml.account_id)
                WHERE (aml.date <= %s) AND
                      (aml.account_id in %s) And
                      (am.state in %s) Group BY aml.account_id""",
                                (str(dateTo) + ' 00:00:00', tuple([Account.id]), tuple(Status),))

            Initial_balance = self.env.cr.fetchall()

            if Initial_balance:
                for ml in Initial_balance:
                    account_id = ml[0]
                    account_date = ml[1]
                    acount_debit = ml[2]
                    account_credit = ml[3]
                    Balance = 0.0
                    Balance = Balance + (acount_debit - account_credit)
                    Vals = {'account_id': account_id,
                            'account_date': account_date,
                            'account_debit': acount_debit,
                            'account_credit': account_credit,
                            'balance': Balance,
                            }
                    mainDict.append(Vals)

        for j in range(len(mainDict)):
            for i in range(len(allData)):
                if allData[i]['account_id'] == mainDict[j]['account_id']:
                    mainDict[j]['account_code'] =  allData[i]['account_code']
                    mainDict[j]['account_name'] =  allData[i]['account_name']
                    mainDict[j]['account_type'] =  allData[i]['account_type']
                    
        new_list = []
        columns = []
        check_ids = []
        dimensiondicts = ''
        res2 = ''
        check_list = ''
        if self.dimension_wise_project == 'month' or self.dimension_wise_project == 'year':
            new_list,dimensiondicts = self.month_year_wise()
            listd = ''
            first_Column_values = new_list[0]
            for i in range(len(new_list)):
                if i == 0:
                    listd = new_list[i]['columns']
                   
            check_list = [(list(c.keys())[0]) for c in listd]
            a1 = [(list(c.keys())[0]) for c in dimensiondicts]
            res = dimensiondicts + [{c:00.0} for c in check_list if c not in a1]
            res2 = sorted(res, key = lambda ele: check_list.index(list(ele.keys())[0]))

        allocated_balance = 0.0
        allcoated_dict = []
        for j in range(len(mainDict)):
            if mainDict[j]['account_type'] in ["Current Year Earnings", "equity_unaffected"]:
                allocated_balance = netcurrentyear
                mainDict[j]['account_name'] = 'Current Year Earnings'
                if netcurrentyear == 0.0 :
                    if res2:
                        mainDict[j]['projects'] = res2
                else:
                    mainDict[j]['balance'] =  netcurrentyear
                    if res2:
                        mainDict[j]['projects'] = res2

                for c in check_list:
                    allcoated_dict.append({c:00.0})
                if dateTo.strftime("%Y") == mainDict[j]['account_date'].strftime("%Y"):
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance':allocated_balance , 'account_code': ' ','account_name': 'Current Year Allocated Earnings', 'account_type': mainDict[j]['account_type'],
                            })
                else:
                    mainDict.append({'account_id': '', 'account_date':mainDict[j]['account_date'],'balance':0.0 , 'account_code': ' ','account_name': 'Current Year Allocated Earnings', 'account_type': mainDict[j]['account_type'],})

                if res2:
                    if mainDict[j]['account_name'] == 'Current Year Allocated Earnings':
                         mainDict[j]['projects'] = allcoated_dict

        fromdate = ''
        if self.dimension_wise_project == 'month':
            listd = []
            first_Column_values = new_list[0]
            for i in range(len(new_list)):
                if i == 0:
                    listd = new_list[i]['columns']
                   

            columns = [{list(c.keys())[0]:00.0} for c in listd]

            for i in range(len(new_list)):
                check_ids.append(new_list[i]['account_id'])

            for j in range(len(mainDict)):
                for i in range(len(new_list)):
                    if mainDict[j]['account_name'] in ["Current Year Earnings", "equity_unaffected"]:
                        continue
                    if mainDict[j]['account_id'] in check_ids:
                        if new_list[i]['account_id'] == mainDict[j]['account_id']:
                            mainDict[j]['projects'] =  new_list[i]['columns']
                    elif mainDict[j]['account_id'] not in check_ids:
                        mainDict[j]['projects'] = columns

            
        if self.dimension_wise_project == 'year':
            fetch_yearwise_data = []
            cur_date = fromdate
            end = dateTo
            listd = ''
            listd = ''
            for i in range(len(new_list)):
                if new_list[i]['account_type'] in ['Bank and Cash', 'asset_cash']:
                    columns = new_list[i]['columns']
                    listd = [list(c.keys())[0] for c in columns]
            fetch_monthwise_data = []
            year = listd[0]
            converted_year = datetime.datetime.strptime(year, "%Y")
            cur_date = converted_year.date()
            while cur_date <= end:
                cur_date_strf = str(cur_date.strftime('%Y') or '')
                cur_date += relativedelta(years=1)
                fetch_yearwise_data.append(cur_date_strf)
            columns = [{i:00.0} for i in fetch_monthwise_data]

            for i in range(len(new_list)):
                check_ids.append(new_list[i]['account_id'])

            for j in range(len(mainDict)):
                for i in range(len(new_list)):
                    if mainDict[j]['account_id'] in check_ids:
                        if new_list[i]['account_id'] == mainDict[j]['account_id']:
                            mainDict[j]['projects'] =  new_list[i]['columns']
                    elif mainDict[j]['account_id'] not in check_ids:
                        mainDict[j]['projects'] = columns

        
        import base64
        dateFrom = self.date_from
        dateTo = self.date_to
        filename = 'Balance Sheet.xls'
        form_name = 'Balance Sheet Between ' + str(dateFrom) + ' to ' + str(dateTo)
        workbook = xlwt.Workbook()
        style = xlwt.XFStyle()
        tall_style = xlwt.easyxf('font:height 720;') # 36pt
        # Create a font to use with the style
        font = xlwt.Font()
        font.name = 'Times New Roman'
        font.bold = True
        font.height = 250
        style.font = font
        xlwt.add_palette_colour("custom_colour", 0x21)
        workbook.set_colour_RGB(0x21, 105, 105, 105)

        xlwt.add_palette_colour("dark_blue", 0x3A)
        workbook.set_colour_RGB(0x3A, 0,0,139)  

        xlwt.add_palette_colour("gainsboro", 0x15)
        workbook.set_colour_RGB(0x15,205,205,205)

        worksheet = workbook.add_sheet("Profit And Loss", cell_overwrite_ok=True)
        worksheet.show_grid = False

        styleheader = xlwt.easyxf('font: bold 1, colour black, height 300;')
        stylecolumnheader = xlwt.easyxf('font: bold 1, colour black, height 200;pattern: pattern solid, fore_colour gainsboro')
        linedata = xlwt.easyxf('borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin; align: horiz right;')
        alinedata = xlwt.easyxf('borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin; align: horiz left;')
        stylecolaccount = xlwt.easyxf('font: bold 1, colour white, height 200; \
                                      pattern: pattern solid, fore_colour dark_blue; \
                                      align: vert centre, horiz centre; \
                                      borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        analytic_st_col = xlwt.easyxf('font: bold 1, colour black, height 200; \
                                    pattern: pattern solid, fore_colour gainsboro; \
                                    align: vert centre, horiz centre; \
                                    borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        general = xlwt.easyxf('font: bold 1, colour black, height 210;')
        dateheader = xlwt.easyxf('font: bold 1, colour black, height 200;')
        maintotal = xlwt.easyxf('font: bold 1, colour black, height 200; \
                borders: top_color black, bottom_color black, right_color black, left_color black, \
        left thin, right thin, top thin, bottom thin;')
        finaltotalheader = xlwt.easyxf('pattern: fore_color white; font: bold 1, colour black; align: horiz right; \
        borders: top_color black, bottom_color black, right_color black, left_color black, \
        left thin, right thin, top thin, bottom thin;')
        rightfont = xlwt.easyxf('pattern: fore_color white; font: color dark_blue; align: horiz right; \
        borders: top_color black, bottom_color black, right_color black, left_color black, \
        left thin, right thin, top thin, bottom thin;')
        floatstyle = xlwt.easyxf("borders: top_color black, bottom_color black, right_color black, left_color black, \
        left thin, right thin, top thin, bottom thin;","#.00")
        finaltotalheaderbold = xlwt.easyxf("pattern: fore_color white; font: bold 1, colour black; \
        borders: top_color black, bottom_color black, right_color black, left_color black, \
        left thin, right thin, top thin, bottom thin;")
        accountnamestyle = xlwt.easyxf('font: bold 1, colour green, height 200;')
        mainheaders = xlwt.easyxf('pattern: fore_color white; font: bold 1, colour dark_blue; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        mainheader = xlwt.easyxf('pattern: pattern solid, fore_colour gainsboro; \
                                 font: bold 1, colour dark_blue; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        mainheaderlinedata = xlwt.easyxf('pattern: pattern solid, fore_colour gainsboro; \
                                 font: bold 1, colour dark_blue; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;',"#.00")
        mainheaderline = xlwt.easyxf("pattern: pattern solid, fore_colour gainsboro; \
                                 font: bold 1, colour dark_blue; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;")
        mainheaderdata = xlwt.easyxf("pattern: fore_color white; font: bold 1, colour dark_blue; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;","#.00")
        mainheaderdatas = xlwt.easyxf("pattern: fore_color white; font: bold 1, colour dark_blue; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;","#.00")
        zero_col = worksheet.col(0)
        zero_col.width = 236 * 22
        first_col = worksheet.col(1)
        first_col.width = 236 * 40
        second_col = worksheet.col(2)
        second_col.width = 236 * 40
        third_col = worksheet.col(3)
        third_col.width = 236 * 25
        fourth_col = worksheet.col(4)
        fourth_col.width = 236 * 20
        fifth_col = worksheet.col(5)
        fifth_col.width = 236 * 20
        sixth_col = worksheet.col(6)
        sixth_col.width = 236 * 20
        seventh_col = worksheet.col(7)
        seventh_col.width = 236 * 20
        #HEADER
        worksheet.row(4).height_mismatch = True
        worksheet.row(4).height = 360
        
        worksheet.write_merge(0, 1, 2, 5, self.env.company.name,styleheader)
        worksheet.write_merge(2, 2, 2, 5, 'Balance Sheet',general)
        headerstring = 'From :' + str(self.date_from.strftime('%d %b %Y') or '') + ' To :' + str(self.date_to.strftime('%d %b %Y') or '')
        worksheet.write_merge(3, 3, 2, 5, headerstring,dateheader)

        row = 4
        ColIndexes = {}
        worksheet.write(row, 0, 'Account  Code', stylecolaccount)
        worksheet.write(row, 1, 'Account Name', stylecolaccount)
        worksheet.write(row, 2, 'Balance', stylecolaccount)
        calc = 4
        col = 3
        colc = 3
      
        if self.dimension_wise_project == 'month':
            listd = ''
            first_Column_values = new_list[0]
            for i in range(len(new_list)):
                if i == 0:
                    listd = new_list[i]['columns']         
            for c in listd:
                dictval = {list(c.keys())[0] : col}
                ColIndexes.update(dictval)
                dyna_col = worksheet.col(col)
                dyna_col.width = 236 * 20
                worksheet.write(row, col, list(c.keys())[0], analytic_st_col)
                col+=1
                calc+=1

        if self.dimension_wise_project == 'year':
            listd = ''
            first_Column_values = new_list[0]
            for i in range(len(new_list)):
                if i == 0:
                    listd = new_list[i]['columns'] 
            for c in listd:
                dictval = {list(c.keys())[0] : col}
                ColIndexes.update(dictval)
                dyna_col = worksheet.col(col)
                dyna_col.width = 236 * 20
                worksheet.write(row, col, list(c.keys())[0], analytic_st_col)
                colc = col
                col+=1
                calc+=1

        current_assets_lists = []
        total_assets = []
        finalassets = []
        total_current_libailities = []
        finalcurrentlibailities = [] 
        totalliabilties = []
        finalliabiltiess = []
        libablitiesequity = []
        totalearning = []
        finalearning = []
        finallibablitiesequity = []
        row+=1
        worksheet.write(row, 0,'ASSETS', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,'', style = mainheader)
        # worksheet.write(row, 3,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheader)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Current Assets', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        # worksheet.write(row, 3,'', style = mainheader)
        # worksheet.write(row, 3,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Bank and Cash Accounts', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        # worksheet.write(row, 3,'', style = mainheader)
        # worksheet.write(row, 3,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        Bank_total_list = []
        TotalBankCash = 0.0
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Bank and Cash', 'asset_cash']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalBankCash += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Bank_total_list.append(listd)
                row+=1
        incomeres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Bank_total_list:
                for j in range(0, len(Bank_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Bank_total_list)):
                        tmp = tmp + Bank_total_list[i][j]
                    incomeres.append(tmp)
        current_assets_lists.append(incomeres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Bank and Cash Accounts', style = mainheaders)
        worksheet.write(row, 2,round((TotalBankCash),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if incomeres:
                for j in range(len(incomeres)):
                    worksheet.write(row, col, round((incomeres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Receivables', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalReceivable = 0.0
        Rec_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Receivable', 'asset_receivable']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalReceivable += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                col = 3
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    if mainDict[s]['projects']:
                        acc_projects = mainDict[s]['projects']
                        listd = []
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2) , style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Rec_total_list.append(listd)
                
                row+=1
        receivableres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Rec_total_list:
                for j in range(0, len(Rec_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Rec_total_list)):
                        tmp = tmp + Rec_total_list[i][j]
                    receivableres.append(tmp)
        current_assets_lists.append(receivableres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Receivables', style = mainheaders)
        worksheet.write(row, 2,round((TotalReceivable),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if receivableres:
                for j in range(len(receivableres)):
                    worksheet.write(row, col, round((receivableres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Current Assets', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalCurrentAsset = 0.0
        Current_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Current Assets', 'asset_current']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalCurrentAsset += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Current_total_list.append(listd)
                    
                row+=1
        currentres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Current_total_list:
                for j in range(0, len(Current_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Current_total_list)):
                        tmp = tmp + Current_total_list[i][j]
                    currentres.append(tmp)
        current_assets_lists.append(currentres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Current Assets', style = mainheaders)
        worksheet.write(row, 2,round((TotalCurrentAsset),2), style = mainheaderdata)
        finalcurrentassets = [sum(i) for i in zip(*current_assets_lists)]
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if currentres:
                for j in range(len(currentres)):
                    worksheet.write(row, col,round((currentres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Prepayments', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalPrePayment = 0.0
        pre_payment_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Prepayments', 'asset_prepayments']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalPrePayment += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        pre_payment_total_list.append(listd)
                    
                row+=1
        prepayments  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if pre_payment_total_list:
                for j in range(0, len(pre_payment_total_list[0])):
                    tmp = 0
                    for i in range(0, len(pre_payment_total_list)):
                        tmp = tmp + pre_payment_total_list[i][j]
                    prepayments.append(tmp)
        pre_payment_total_list.append(prepayments)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Pre Payments', style = mainheaders)
        worksheet.write(row, 2,round((TotalPrePayment),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if prepayments:
                for j in range(len(prepayments)):
                    worksheet.write(row, col,round((prepayments[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        total_assets.append(finalcurrentassets)
        TotalCurrentAssets = TotalBankCash + TotalReceivable + TotalCurrentAsset + TotalPrePayment
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Current Assets', style = mainheaders)
        worksheet.write(row, 2,round((TotalCurrentAssets),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finalcurrentassets:
                for j in range(len(finalcurrentassets)):
                    worksheet.write(row, col,round((finalcurrentassets[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Plus Fixed Assets', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalFixedAssets = 0.0
        Fixed_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Fixed Assets', 'asset_fixed']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalFixedAssets += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Fixed_total_list.append(listd)

                row+=1
        fixedres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Fixed_total_list:
                for j in range(0, len(Fixed_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Fixed_total_list)):
                        tmp = tmp + Fixed_total_list[i][j]
                    fixedres.append(tmp)
        total_assets.append(fixedres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Fixed Assets', style = mainheaders)
        worksheet.write(row, 2,round((TotalFixedAssets),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if fixedres:
                for j in range(len(fixedres)):
                    worksheet.write(row, col,round((fixedres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Plus Non-current Assets', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalNonCurrentAssets = 0.0
        NonCurrent_total_list = []
        # ================================================================
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Non-current Assets', 'asset_non_current']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalNonCurrentAssets += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        NonCurrent_total_list.append(listd)

                row+=1
        noncurrentres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Fixed_total_list:
                for j in range(0, len(NonCurrent_total_list[0])):
                    tmp = 0
                    for i in range(0, len(NonCurrent_total_list)):
                        tmp = tmp + NonCurrent_total_list[i][j]
                    noncurrentres.append(tmp)
        total_assets.append(noncurrentres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Plus Non-current Assets', style = mainheaders)
        worksheet.write(row, 2,round((TotalNonCurrentAssets),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if noncurrentres:
                for j in range(len(noncurrentres)):
                    worksheet.write(row, col,round((noncurrentres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        finalassets = [sum(i) for i in zip(*total_assets)]
        TotalAssets = TotalCurrentAssets + TotalFixedAssets + TotalNonCurrentAssets
        worksheet.write(row, 0,'Total Assets', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,round((TotalAssets),2), style = mainheaderlinedata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finalassets:
                for j in range(len(finalassets)):
                        worksheet.write(row, col,round((finalassets[j]),2), mainheaderlinedata)
                        col+=1
        row +=1
        worksheet.write(row, 0,'LIABILITIES', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheader)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Current Liabilities', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Current Liabilities', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalCurrentLiability = 0.0
        Liabilities_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Current Liabilities', 'liability_current']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalCurrentLiability += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((abs(mainDict[s]['balance'])),1) ,floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((abs(list(pr.values())[0])),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Liabilities_total_list.append(listd)

                row+=1
        liabilitiesres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Liabilities_total_list:
                for j in range(0, len(Liabilities_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Liabilities_total_list)):
                        tmp = tmp + Liabilities_total_list[i][j]
                    liabilitiesres.append(tmp)
        total_current_libailities.append(liabilitiesres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Current Liabilities', style = mainheaders)
        worksheet.write(row, 2,round(abs(TotalCurrentLiability),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if liabilitiesres:
                for j in range(len(liabilitiesres)):
                    worksheet.write(row, col,round((abs(liabilitiesres[j])),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((abs(00.0)),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Payables', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row+=1
        TotalPayables = 0.0
        Payables_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Payable', 'liability_payable']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalPayables += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((abs(mainDict[s]['balance'])),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,abs(list(pr.values())[0]), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Payables_total_list.append(listd)
                row+=1
        payablesres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Payables_total_list:
                for j in range(0, len(Payables_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Payables_total_list)):
                        tmp = tmp + Payables_total_list[i][j]
                    payablesres.append(tmp)
        total_current_libailities.append(liabilitiesres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Payables', style = mainheaders)
        worksheet.write(row, 2,round(abs(TotalPayables),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if payablesres:
                for j in range(len(payablesres)):
                    worksheet.write(row, col,round((abs(payablesres[j])),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((abs(00.0)),2),mainheaderdata)
                    col+=1
        row +=1
        finalcurrentlibailities = [sum(i) for i in zip(*total_current_libailities)]
        totalliabilties.append(finalcurrentlibailities)
        TotalCurrentLiabilities = TotalCurrentLiability + TotalPayables
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'TotalCurrentLiabilities', style = mainheaders)
        worksheet.write(row, 2,round((abs(TotalCurrentLiabilities)),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finalcurrentlibailities:
                for j in range(len(finalcurrentlibailities)):
                    worksheet.write(row, col,round((abs(finalcurrentlibailities[j])),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Plus Non-current Liabilities', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        # worksheet.write(row, 3,'', style = mainheader)
        # worksheet.write(row, 3,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        # ================================================================
        TotalNonCurrentLiabilities = 0.0
        NonCurrentLib_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Non-current Liabilities', 'asset_non_current']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalNonCurrentLiabilities += mainDict[s]['balance']
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round(-abs(mainDict[s]['balance']),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        listd = []
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        NonCurrentLib_total_list.append(listd)

                row+=1
        noncurrentlibres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if NonCurrentLib_total_list:
                for j in range(0, len(NonCurrentLib_total_list[0])):
                    tmp = 0
                    for i in range(0, len(NonCurrentLib_total_list)):
                        tmp = tmp + NonCurrentLib_total_list[i][j]
                    noncurrentlibres.append(tmp)
        total_assets.append(noncurrentlibres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Non-current Liabilities', style = mainheaders)
        worksheet.write(row, 2,round(-abs(TotalNonCurrentLiabilities),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if noncurrentlibres:
                for j in range(len(noncurrentlibres)):
                    worksheet.write(row, col,round((noncurrentlibres[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        TotalCurrentLiabilities += TotalNonCurrentLiabilities
        if TotalNonCurrentLiabilities == 0.0:
            TotalCurrentLiabilities = abs(TotalCurrentLiabilities)
        else:
            TotalCurrentLiabilities = -abs(TotalCurrentLiabilities)
        # ===========================================================================
        worksheet.write(row, 0,'Total LIABILITIES', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,round((TotalCurrentLiabilities),2), style = mainheaderlinedata)
        # worksheet.write(row, 3,'', style = mainheader)
        totalliabilties.append(finalcurrentlibailities)
        finalliabiltiess = [sum(i) for i in zip(*totalliabilties)]
        libablitiesequity.append(finalliabiltiess)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finalliabiltiess:
                for j in range(len(finalliabiltiess)):
                    worksheet.write(row, col,round((abs(finalliabiltiess[j])),2), mainheaderlinedata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((abs(00.0)),2),mainheaderlinedata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'EQUITY', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,'', style = mainheader)
        # worksheet.write(row, 3,'', style = mainheader)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheader)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Unallocated Earnings', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Current Year Unallocated Earnings', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalCurrentYearEarnings = 0.0
        Earnings_total_list = []
            # print("mainDict[s]['account_name']====",mainDict[s]['account_name'])
                # if mainDict[s]['balance'] == 00.0:
                #     continue
                # if mainDict[s]['account_name'] in ["Current Year Earnings", "equity_unaffected"]:
                #     print("netcurrentyear======",netcurrentyear)
                #     if netcurrentyear == 0.0:
                #         TotalCurrentYearEarnings += 0.0
                #     else:
                #         print("dateTo.strftime=====",dateTo.strftime("%Y"))
                #         print("mainDict[j]['account_date'].strftime=======",mainDict[s]['account_date'].strftime("%Y"))
                #         if dateTo.strftime("%Y") == mainDict[s]['account_date'].strftime("%Y"):

                #             TotalCurrentYearEarnings += 0.0
                #         else:
                #             TotalCurrentYearEarnings = mainDict[s]['balance']
        worksheet.write(row, 0, '9999',style = alinedata)
        worksheet.write(row, 1, 'Current Year Earnings',style = alinedata)
        worksheet.write(row, 2, netcurrentyear,style = floatstyle)
        row +=1
        worksheet.write(row, 0, '9999',style = alinedata)
        worksheet.write(row, 1, 'Current Year Allocated Earnings',style = alinedata)
        worksheet.write(row, 2, abs(current_year_allocated_balance),style = floatstyle)
        row +=1
        TotalCurrentYearEarnings = netcurrentyear + abs(current_year_allocated_balance)
        for s in range(len(mainDict)):
            # if netcurrentyear == 0.0:
            #     worksheet.write(row, 2, round((00.0),1),floatstyle)
            # else:
            #     worksheet.write(row, 2, round((mainDict[s]['balance']),1),floatstyle)
            if mainDict[s]['account_type'] in ["Current Year Earnings", "equity_unaffected"]:
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    acc_projects = mainDict[s]['projects']
                    if acc_projects:
                        listd = []
                        for pr in acc_projects:
                            if mainDict[s]['account_name'] in ["Current Year Earnings", "equity_unaffected"]:
                                if netcurrentyear == 0.0:
                                    worksheet.write(row, col,0.0, style = floatstyle)
                                else:
                                    if dateTo.strftime("%Y") == mainDict[j]['account_date'].strftime("%Y"):
                                        worksheet.write(row, col,0, style = floatstyle)
                                    else:
                                        worksheet.write(row, col,list(pr.values())[0], style = floatstyle)

                            if mainDict[s]['account_name'] == 'Current Year Allocated Earnings':
                                if netcurrentyear == 0.0:
                                    worksheet.write(row, col,0.0, style = floatstyle)
                                else:
                                    if dateTo.strftime("%Y") == mainDict[j]['account_date'].strftime("%Y"):
                                        worksheet.write(row, col,0, style = floatstyle)
                                    else:
                                        worksheet.write(row, col,round((list(pr.values())[0]),2), style = floatstyle)
                            col+=1
                        if netcurrentyear == 0.0:
                            listd = [0 for c in acc_projects]
                            Earnings_total_list.append(listd)
                        else:
                            if dateTo.strftime("%Y") == mainDict[j]['account_date'].strftime("%Y"):
                                listd = [0 for c in acc_projects]
                                Earnings_total_list.append(listd)
                            else:
                                listd = [list(c.values())[0] for c in acc_projects]
                                Earnings_total_list.append(listd)
                    row+=1
        earningsres  = []
        totalunallocatedearnings = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Earnings_total_list:
                for j in range(0, len(Earnings_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Earnings_total_list)):
                        tmp = tmp + Earnings_total_list[i][j]
                    earningsres.append(tmp)

        totalearning.append(earningsres)
        totalunallocatedearnings.append(earningsres)
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Current Year Unallocated Earnings', style = mainheaders)
        if netcurrentyear == 0.0:
            worksheet.write(row, 2,0.0, style = mainheaderdata)
        else:
            worksheet.write(row, 2,round((TotalCurrentYearEarnings),2), style = mainheaderdata)
        if Projectwise == 'month' or Projectwise == 'year':
            col = 3
            if netcurrentyear == 0.0:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
            else:
                if earningsres:
                    for j in range(len(earningsres)):
                        worksheet.write(row, col,round((earningsres[j]),2), mainheaderdata)
                        col+=1
                else:
                    for p,v in ColIndexes.items():
                        worksheet.write(row, col, round((00.0),2),mainheaderdata)
                        col+=1
            col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Previous Years Unallocated Earnings', style = mainheaders)
        worksheet.write(row, 2, round((netpreviousyear),2), style = mainheaderdata)
        # if netcurrentyear == 0.0:
        # else:
        #     worksheet.write(row, 2, 0.0, style = mainheaderdata)
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            col = 3
            if netcurrentyear == 0.0:
                if res2:
                    listd = [list(j.values())[0] for j in res2]
                    totalunallocatedearnings.append(listd)
                    for j in res2:
                        worksheet.write(row, col,round((list(j.values())[0]),2), mainheaderdata)
                        col+=1
                else:
                    for p,v in ColIndexes.items():
                        worksheet.write(row, col, round((00.0),2),mainheaderdata)
                        col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2) ,mainheaderdata)
                    col+=1
            col+=1
        row +=1

        TotalUnallocatedEarnings = TotalCurrentYearEarnings + netpreviousyear
        finalunallocatedearnings = []
        allfinalunallocated = []
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Unallocated Earnings', style = mainheaders)
        worksheet.write(row, 2, round((TotalUnallocatedEarnings),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if totalunallocatedearnings:
                finalunallocatedearnings = [sum(i) for i in zip(*totalunallocatedearnings)]
                allfinalunallocated.append(finalunallocatedearnings)
                for j in range(len(finalunallocatedearnings)):
                    worksheet.write(row, col,round((finalunallocatedearnings[j]),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderdata)
                    col+=1
        row +=1
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Retained Earnings', style = mainheaders)
        worksheet.write(row, 2,'', style = mainheaders)
        for i in range(3,100):
          if i != col:
              worksheet.write(row, i,'',style = mainheaders)
          elif i == col:
              break
        row +=1
        TotalRetainedEarnings = 0.0
        Equity_total_list = []
        for s in range(len(mainDict)):
            if mainDict[s]['account_type'] in ['Equity', 'equity']:
                if mainDict[s]['balance'] == 00.0:
                    continue
                TotalRetainedEarnings += (-mainDict[s]['balance'])
                worksheet.write(row, 0, mainDict[s]['account_code'],alinedata)
                worksheet.write(row, 1, mainDict[s]['account_name'],alinedata)
                worksheet.write(row, 2, round((abs(mainDict[s]['balance'])),2),floatstyle)
                if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
                    col = 3
                    if mainDict[s]['projects']:
                        acc_projects = mainDict[s]['projects']
                        for pr in acc_projects:
                            worksheet.write(row, col,round((abs(list(pr.values())[0])),2), style = floatstyle)
                            col+=1
                        listd = [list(c.values())[0] for c in acc_projects]
                        Equity_total_list.append(listd)
                row+=1
        equityres  = []
        if Projectwise == 'dimension' or Projectwise == 'month' or Projectwise == 'year':
            if Equity_total_list:
                for j in range(0, len(Equity_total_list[0])):
                    tmp = 0
                    for i in range(0, len(Equity_total_list)):
                        tmp = tmp + Equity_total_list[i][j]
                    equityres.append(tmp)
        TotalEquity = TotalUnallocatedEarnings + TotalRetainedEarnings
        worksheet.write(row, 0,'', style = mainheaders)
        worksheet.write(row, 1,'Total Retained Earnings', style = mainheaders)
        worksheet.write(row, 2,round((TotalRetainedEarnings),2), style = mainheaderdata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if equityres:
                for j in range(len(equityres)):
                    worksheet.write(row, col,round((abs(equityres[j])),2), mainheaderdata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((abs(00.0)),2),mainheaderdata)
                    col+=1
        row +=1
        allfinalunallocated.append(equityres)
        finalearning = [sum(i) for i in zip(*allfinalunallocated)]
        libablitiesequity.append(finalearning)
        worksheet.write(row, 0,'Total EQUITY', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,round((abs(TotalEquity)),2), style = mainheaderlinedata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finalearning:
                for j in range(len(finalearning)):
                    worksheet.write(row, col,round((abs(finalearning[j])),2), mainheaderlinedata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((abs(00.0)),2),mainheaderlinedata)
                    col+=1
        row +=1
        finallibablitiesequity = [sum(i) for i in zip(*libablitiesequity)]
        TotalEquityLiabilities = TotalEquity + TotalCurrentLiabilities
        worksheet.write(row, 0,'LIABILITIES + EQUITY', style = mainheader)
        worksheet.write(row, 1,'', style = mainheader)
        worksheet.write(row, 2,round((TotalEquityLiabilities),2), style = mainheaderlinedata)
        col = 3
        if Projectwise == 'dimension'or Projectwise == 'month' or Projectwise == 'year':
            if finallibablitiesequity:
                for j in range(len(finallibablitiesequity)):
                    worksheet.write(row, col,round((finallibablitiesequity[j]),2), mainheaderlinedata)
                    col+=1
            else:
                for p,v in ColIndexes.items():
                    worksheet.write(row, col, round((00.0),2),mainheaderlinedata)
                    col+=1
        row +=1
  
        buffer = io.BytesIO()
        workbook.save(buffer)
        export_id = self.env['balance.sheet.excel'].create(
                        {'excel_file': base64.encodebytes(buffer.getvalue()), 'file_name': filename})
        buffer.close()

        return {
            'name': form_name,
            'res_id': export_id.id,
            'res_model': 'balance.sheet.excel',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
            }


class balance_sheet_export_excel(models.TransientModel):
    _name= "balance.sheet.excel"
    _description = "Balance Sheet Excel Report"

    excel_file = fields.Binary('Report for Balance Sheet')
    file_name = fields.Char('File', size=64)
