from presidio_analyzer.nlp_engine import NlpEngine
from presidio_analyzer.predefined_recognizers import (
    AuAbnRecognizer,
    AuAcnRecognizer,
    AuMedicareRecognizer,
    AuTfnRecognizer,
    CreditCardRecognizer,
    CryptoRecognizer,
    DateRecognizer,
    EmailRecognizer,
    EsNieRecognizer,
    EsNifRecognizer,
    FiPersonalIdentityCodeRecognizer,
    IbanRecognizer,
    InAadhaarRecognizer,
    InPanRecognizer,
    InVehicleRegistrationRecognizer,
    InVoterRecognizer,
    InPassportRecognizer,
    IpRecognizer,
    ItFiscalCodeRecognizer,
    ItVatCodeRecognizer,
    MedicalLicenseRecognizer,
    NhsRecognizer,
    PhoneRecognizer,
    PlPeselRecognizer,
    SgFinRecognizer,
    SgUenRecognizer,
    UrlRecognizer,
    UsItinRecognizer,
    UsSsnRecognizer,
    UsBankRecognizer,
    UsLicenseRecognizer,
    UsPassportRecognizer,
)
from .recognizer_registry import RecognizerRegistry


class PrivacyPillarRecognizerRegistry(RecognizerRegistry):
    """Load predefined recognizers iff entity matches"""
    PREDEFINED_RECOGNIZERS_MAP = {
        "AU_ABN": AuAbnRecognizer,
        "AU_ACN": AuAcnRecognizer,
        "AU_MEDICARE": AuMedicareRecognizer,
        "AU_TFN": AuTfnRecognizer,
        "CREDIT_CARD": CreditCardRecognizer,
        "CRYPTO": CryptoRecognizer,
        "DATE_TIME": DateRecognizer,
        "EMAIL_ADDRESS": EmailRecognizer,
        "ES_NIE": EsNieRecognizer,
        "ES_NIF": EsNifRecognizer,
        "FI_PERSONAL_IDENTITY_CODE": FiPersonalIdentityCodeRecognizer,
        "IBAN_CODE": IbanRecognizer,
        "IN_AADHAAR": InAadhaarRecognizer,
        "IN_PAN": InPanRecognizer,
        "IN_VEHICLE_REGISTRATION": InVehicleRegistrationRecognizer,
        "IN_VOTER": InVoterRecognizer,
        "IN_PASSPORT": InPassportRecognizer,
        "IP_ADDRESS": IpRecognizer,
        "IT_FISCAL_CODE": ItFiscalCodeRecognizer,
        "IT_VAT_CODE": ItVatCodeRecognizer,
        "MEDICAL_LICENSE": MedicalLicenseRecognizer,
        "PHONE_NUMBER": PhoneRecognizer,
        "PL_PESEL": PlPeselRecognizer,
        "SG_NRIC_FIN": SgFinRecognizer,
        "SG_UEN": SgUenRecognizer,
        "UK_NHS": NhsRecognizer,
        "URL": UrlRecognizer,
        "US_BANK_NUMBER": UsBankRecognizer,
        "US_DRIVER_LICENSE": UsLicenseRecognizer,
        "US_PASSPORT": UsPassportRecognizer,
        "US_ITIN": UsItinRecognizer,
        "US_SSN": UsSsnRecognizer,
    }

    def __init__(self, languages: list[str], nlp_engine: NlpEngine, entities: list[str]):
        super().__init__()
        candidate_entities = set(self.PREDEFINED_RECOGNIZERS_MAP.keys()) & set(entities)
        nlp_recognizer_class = self._get_nlp_recognizer(nlp_engine)

        for lang in languages:
            predefined_recognizers = [
                self._RecognizerRegistry__instantiate_recognizer(
                    recognizer_class=self.PREDEFINED_RECOGNIZERS_MAP[entity],
                    supported_language=lang,
                )
                for entity in candidate_entities
            ]
            self.recognizers.extend(predefined_recognizers)

            nlp_recognizer_inst = nlp_recognizer_class(
                supported_language=lang,
                supported_entities=nlp_engine.get_supported_entities(),
            )
            self.recognizers.append(nlp_recognizer_inst)
 