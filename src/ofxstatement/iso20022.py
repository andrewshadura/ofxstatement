from datetime import datetime
from xml.etree import ElementTree as etree


class Iso20022Writer(object):
    statement = None
    tb = None
    genTime = None

    def __init__(self, statement):
        self.statement = statement
        self.genTime = datetime.now()

    def toxml(self):
        self.tb = etree.TreeBuilder()
        et = self.buildDocument()
        encoded = etree.tostring(et.getroot(), "utf-8")
        encoded = str(encoded, "utf-8")
        header = ('<?xml version="1.0" encoding="UTF-8"?>\n')

        return header + encoded

    def buildDocument(self):
        tb = self.tb
        tb.start("Document", {
            'xmlns:xsd': "http://www.w3.org/2001/XMLSchema",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xmlns': "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"
        })
        tb.start("BkToCstmrStmt")

        self.buildHeader()

        self.buildTransactionList()

        tb.end("BkToCstmrStmt")
        tb.end("Document")
        return etree.ElementTree(tb.close())

    def buildHeader(self):
        tb = self.tb
        tb.start("GrpHdr", {})
        self.buildText("MsgId", self.statement.bank_id + '-' + self.genTime.date().isoformat() + '-0000000')
        self.buildDateTime("CreDtTm", self.genTime)
        tb.start("MsgPgntn", {})
        self.buildText("PgNb", "1")
        self.buildText("LastPgInd", "true")
        tb.end("MsgPgntn")

        tb.end("GrpHdr")

    def buildTransactionList(self):
        tb = self.tb
        tb.start("Stmt", {})

        self.buildText("Id", "0")
        self.buildText("ElctrncSeqNb", "0")
        self.buildDateTime("CreDtTm", self.genTime)

        tb.start("Acct", {})
        self.buildText("Ccy", self.statement.currency)
        tb.start("Svcr", {})
        tb.start("FinInstnId", {})
        self.buildText("BIC", self.statement.bank_id, False)
        tb.end("FinInstnId")
        tb.end("Svcr")
        self.buildText("Id", self.statement.account_id, False)
        self.buildText("Tp", "CACC")
        tb.end("Acct")

        if self.statement.start_date is not None:
            tb.start("FrToDt", {})
            self.buildDateTime("FrDtTm", self.statement.start_date, False)
            self.buildDateTime("ToDtTm", self.statement.end_date, False)
            tb.end("FrToDt")

        tb.start("Bal", {})
        tb.start("Tp", {})
        tb.start("CdOrPrtry", {})
        self.buildText("Cd", "PRCD")
        tb.end("CdOrPrtry")
        tb.end("Tp")
        self.buildAmount("Amt", self.statement.start_balance, False, self.statement.currency)
        self.buildText("CdtDbtInd", "DBIT" if self.statement.start_balance < 0 else "CRDT")
        tb.start("Dt", {})
        self.buildDate("Dt", self.statement.start_date, False)
        tb.end("Dt")
        tb.end("Bal")

        tb.start("Bal", {})
        tb.start("Tp", {})
        tb.start("CdOrPrtry", {})
        self.buildText("Cd", "PRCD")
        tb.end("CdOrPrtry")
        tb.end("Tp")
        self.buildAmount("Amt", self.statement.end_balance, False, self.statement.currency)
        self.buildText("CdtDbtInd", "DBIT" if self.statement.start_balance < 0 else "CRDT")
        tb.start("Dt", {})
        self.buildDate("Dt", self.statement.end_date, False)
        tb.end("Dt")
        tb.end("Bal")

        for line in self.statement.lines:
            self.buildTransaction(line)

        tb.end("Stmt")

    def buildTransaction(self, line):
        tb = self.tb
        tb.start("Ntry", {})

        self.buildText("CdtDbtInd", "DBIT" if line.amount < 0 else "CRDT")
        self.buildText("Sts", "BOOK")
        tb.start("BookgDt", {})
        self.buildDate("Dt", line.date_user)
        tb.end("BookgDt")
        tb.start("ValDt", {})
        self.buildDate("Dt", line.date)
        tb.end("ValDt")
        self.buildText("AcctSvcrRef", line.id)
        self.buildAmount("Amt", line.amount, self.statement.currency)
        self.buildText("AddtlNtryInf", line.memo)
        tb.start("NtryDtls", {})
        tb.start("TxDtls", {})
        tb.start("Refs", {})
        self.buildText("EndToEndId", line.refnum)
        tb.end("Refs")
        tb.end("TxDtls")
        tb.end("NtryDtls")
        tb.start("RltdPties", {})
        if line.amount < 0:
            tb.start("CdtrAcct", {})
        else:
            tb.start("DbtrAcct", {})
        if line.bank_account_to:
            tb.start("Id", {})
            self.buildText("IBAN", line.bank_account_to.acct_id)
            tb.end("Id")
        self.buildText("Nm", line.payee)
        if line.amount < 0:
            tb.end("CdtrAcct")
        else:
            tb.end("DbtrAcct")
        tb.end("RltdPties")

        tb.end("Ntry")

    def buildText(self, tag, text, skipEmpty=True, attr={}):
        if not text and skipEmpty:
            return
        self.tb.start(tag, attr)
        self.tb.data(text or "")
        self.tb.end(tag)

    def buildDate(self, tag, dt, skipEmpty=True):
        if not dt and skipEmpty:
            return
        if dt is None:
            self.buildText(tag, "", skipEmpty)
        else:
            self.buildText(tag, dt.date().isoformat())

    def buildDateTime(self, tag, dt, skipEmpty=True):
        if not dt and skipEmpty:
            return
        if dt is None:
            self.buildText(tag, "", skipEmpty)
        else:
            self.buildText(tag, dt.replace(microsecond=0).isoformat())

    def buildAmount(self, tag, amount, skipEmpty=True, currency=None):
        if amount is None and skipEmpty:
            return
        if currency is not None:
            attr = {"Ccy": currency}
        else:
            attr = {}
        if amount is None:
            self.buildText(tag, "", skipEmpty)
        else:
            self.buildText(tag, "%.2f" % (amount if amount > 0 else -amount), attr=attr)
