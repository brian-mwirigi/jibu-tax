import httpx

from app.config import Settings, get_settings
from app.schemas.kra import TaxpayerResponse


DEMO_REGISTRY = {
    "P051234567M": {
        "name": "SAFARI HOTEL LIMITED",
        "type": "company",
        "vat_registered": True,
        "etims_onboarded": True,
    },
    "A012345678W": {
        "name": "JIBUTAX DEMO TRADER",
        "type": "individual",
        "vat_registered": True,
        "etims_onboarded": True,
    },
}


class KRAService:
    async def verify_pin(
        self,
        pin: str,
    ) -> TaxpayerResponse:
        settings = get_settings()

        if settings.kra_environment == "sandbox":
            return await self._verify_demo_pin(pin)

        return await self._verify_live_pin(
            pin=pin,
            settings=settings,
        )

    async def _verify_demo_pin(
        self,
        pin: str,
    ) -> TaxpayerResponse:
        taxpayer = DEMO_REGISTRY.get(pin)

        if taxpayer is None:
            return TaxpayerResponse(
                valid=False,
                pin=pin,
                message=(
                    "PIN was not found in the demo registry"
                ),
            )

        return TaxpayerResponse(
            valid=True,
            pin=pin,
            taxpayer_name=taxpayer["name"],
            taxpayer_type=taxpayer["type"],
            vat_registered=taxpayer["vat_registered"],
            etims_onboarded=taxpayer["etims_onboarded"],
            message="PIN verification completed",
        )

    async def _verify_live_pin(
        self,
        pin: str,
        settings: Settings,
    ) -> TaxpayerResponse:
        if settings.kra_api_key is None:
            raise RuntimeError(
                "KRA API key is not configured"
            )

        api_key = settings.kra_api_key

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        timeout = httpx.Timeout(
            connect=2.0,
            read=5.0,
            write=5.0,
            pool=2.0,
        )

        async with httpx.AsyncClient(
            base_url=settings.kra_api_base_url,
            timeout=timeout,
        ) as client:
            response = await client.get(
                "/taxpayer/pin",
                params={"pin": pin},
                headers=headers,
            )

        response.raise_for_status()
        data = response.json()

        return TaxpayerResponse(
            valid=bool(data.get("valid")),
            pin=pin,
            taxpayer_name=data.get("name"),
            taxpayer_type=data.get("type"),
            vat_registered=bool(
                data.get("vat_registered")
            ),
            etims_onboarded=bool(
                data.get("etims_onboarded")
            ),
            message="PIN verification completed",
        )