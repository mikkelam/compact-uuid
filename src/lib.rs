use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
use pgrx::prelude::*;
use std::ffi::{CStr, CString};

pgrx::pg_module_magic!();

pgrx::extension_sql_file!("../sql/compact_uuid.sql", bootstrap);

fn decode(value: &str) -> Result<[u8; 16], String> {
    if value.len() == 22 {
        let bytes = URL_SAFE_NO_PAD.decode(value).map_err(|e| e.to_string())?;
        bytes.try_into().map_err(|_| "expected 16 bytes".into())
    } else if value.len() == 36 {
        uuid::Uuid::parse_str(value)
            .map(|u| *u.as_bytes())
            .map_err(|e| e.to_string())
    } else {
        Err("expected 22 Base64url characters or a hyphenated UUID".into())
    }
}

// The SQL declarations use compact_uuid; its fixed-size Datum layout matches Uuid.
#[pg_extern(immutable, strict, parallel_safe, sql = false)]
fn compact_uuid_in(input: &CStr) -> pgrx::Uuid {
    let parsed = input.to_str().map_err(|e| e.to_string()).and_then(decode);
    match parsed {
        Ok(bytes) => pgrx::Uuid::from_bytes(bytes),
        Err(reason) => {
            pgrx::ereport!(
                pgrx::PgLogLevel::ERROR,
                pgrx::PgSqlErrorCode::ERRCODE_INVALID_TEXT_REPRESENTATION,
                format!("invalid input syntax for compact_uuid: {reason}")
            );
            unreachable!()
        }
    }
}

#[pg_extern(immutable, strict, parallel_safe, sql = false)]
fn compact_uuid_out(value: pgrx::Uuid) -> CString {
    CString::new(URL_SAFE_NO_PAD.encode(value.as_bytes())).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_encoding_and_uuid_input() {
        let bytes = decode("550e8400-e29b-41d4-a716-446655440000").unwrap();
        assert_eq!(URL_SAFE_NO_PAD.encode(bytes), "VQ6EAOKbQdSnFkRmVUQAAA");
        assert_eq!(decode("VQ6EAOKbQdSnFkRmVUQAAA").unwrap(), bytes);
    }

    #[test]
    fn rejects_noncanonical_trailing_bits_padding_and_alphabet() {
        for value in [
            "VQ6EAOKbQdSnFkRmVUQAAB",
            "VQ6EAOKbQdSnFkRmVUQAAA==",
            "////////T/+//////////w",
            "short",
            "550e8400e29b41d4a716446655440000",
        ] {
            assert!(decode(value).is_err(), "accepted {value}");
        }
    }

    #[test]
    fn all_byte_values_and_extremes_roundtrip() {
        for byte in 0..=255u8 {
            let bytes = [byte; 16];
            let encoded = URL_SAFE_NO_PAD.encode(bytes);
            assert_eq!(encoded.len(), 22);
            assert_eq!(decode(&encoded).unwrap(), bytes);
        }
    }
}
