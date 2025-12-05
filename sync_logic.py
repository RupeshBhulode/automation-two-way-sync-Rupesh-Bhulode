import logging

logger = logging.getLogger("sync")

SHEET_TO_TRELLO = {
    "new": "todo",
    "contacted": "inprogress",
    "qualified": "done",
    "lost": None,   
}

TRELLO_TO_SHEET = {
    "todo": "new",
    "inprogress": "contacted",
    "done": "qualified",
}


def sync_sheet_to_trello(sheet, trello, mappings, state, save_state_callback, data_json_path):
    
    rows = sheet.read_rows()
    for r in rows:
        sid_raw = r.get("id")
        if sid_raw is None or str(sid_raw).strip() == "":
            continue
        sid = str(sid_raw).strip()
        name = str(r.get("name", "")).strip()
        email = str(r.get("email", "")).strip()
        note = str(r.get("note", "")).strip()
        source = str(r.get("source", "")).strip()
        sheet_category_raw = str(r.get("category", "")).strip().lower()

        mapped_list_for_sheet = SHEET_TO_TRELLO.get(sheet_category_raw)

        if sid not in mappings:
            if mapped_list_for_sheet:
                card_name = f"{name} (LeadID: {sid})"
                desc_fields = {"Email": email, "Note": note, "Source": source}
                desc = trello.render_fields_to_desc(desc_fields)
                try:
                    card_id = trello.create_card(mapped_list_for_sheet, card_name, desc)
                    mappings[sid] = {
                        "card_id": card_id,
                        "category": sheet_category_raw,
                        "name": name,
                        "email": email,
                        "note": note,
                        "source": source
                    }
                    save_state_callback(data_json_path, state)
                    logger.info("Created card for sheet id=%s -> trello card id=%s (list=%s)", sid, card_id,
                                mapped_list_for_sheet)
                except Exception as e:
                    logger.exception("Failed creating card for sheet id=%s: %s", sid, e)
            else:
                logger.info("Sheet id=%s is LOST; not creating Trello card (by design)", sid)
        else:
            mapped = mappings[sid]
            mapped_category = (mapped.get("category") or "").strip().lower()
            card_id = mapped.get("card_id")

            if sheet_category_raw != mapped_category:
                if mapped_list_for_sheet is None:
                    if card_id:
                        try:
                            trello.archive_card(card_id)
                            logger.info("Archived Trello card %s because sheet id %s changed to LOST", card_id, sid)
                        except Exception as e:
                            logger.exception("Failed to archive Trello card %s for sid %s: %s", card_id, sid, e)
                    mappings.pop(sid, None)
                    save_state_callback(data_json_path, state)
                else:
                    try:
                        trello.get_lists_by_name()
                        if not card_id:
                            card_name = f"{name} (LeadID: {sid})"
                            desc = trello.render_fields_to_desc({"Email": email, "Note": note, "Source": source})
                            card_id = trello.create_card(mapped_list_for_sheet, card_name, desc)
                            mappings[sid] = {
                                "card_id": card_id,
                                "category": sheet_category_raw,
                                "name": name,
                                "email": email,
                                "note": note,
                                "source": source
                            }
                            save_state_callback(data_json_path, state)
                            logger.info("Re-created Trello card for sheet id=%s -> %s", sid, card_id)
                        else:
                            trello.move_card(card_id, mapped_list_for_sheet)
                            trello.update_card_fields(card_id, {"email": email, "note": note, "source": source})
                            mapped["category"] = sheet_category_raw
                            mapped["name"] = name
                            mapped["email"] = email
                            mapped["note"] = note
                            mapped["source"] = source
                            save_state_callback(data_json_path, state)
                            logger.info(
                                "Moved Trello card %s -> list %s (sheet id %s changed category)", card_id,
                                mapped_list_for_sheet, sid)
                    except Exception as e:
                        logger.exception("Failed handling category change for sid %s: %s", sid, e)

           
            mapped_name = (mapped.get("name") or "").strip()
            if name  != mapped_name and card_id:
                try:
                    trello.update_card_name(card_id, f"{name} (LeadID: {sid})")
                    mapped["name"] = name
                    save_state_callback(data_json_path, state)
                    logger.info("Updated Trello card %s title -> %s (due to sheet change)", card_id, name)
                except Exception as e:
                    logger.exception("Failed to update Trello card title for %s: %s", card_id, e)

            
            if card_id:
                to_update = {}
                if email != (mapped.get("email") or "").strip():
                    to_update["email"] = email
                if note != (mapped.get("note") or "").strip():
                    to_update["note"] = note
                if source != (mapped.get("source") or "").strip():
                    to_update["source"] = source
                if to_update:
                    try:
                        trello.update_card_fields(card_id, to_update)
                        mapped.update(
                            {k: v for k, v in {"email": email, "note": note, "source": source}.items() if
                             (k in to_update)})
                        save_state_callback(data_json_path, state)
                        logger.info("Updated Trello card %s desc fields -> %s", card_id, list(to_update.keys()))
                    except Exception as e:
                        logger.exception("Failed to update Trello card desc for %s: %s", card_id, e)


def sync_trello_to_sheet(sheet, trello, mappings, state, save_state_callback, data_json_path):
    
    try:
        cards = trello.get_cards_on_board()
        lists = trello.get_lists_by_name()
        list_id_to_name = {v: k for k, v in lists.items()}
        cards_by_id = {c.get("id"): c for c in cards}

        for sid, mapped in list(mappings.items()):
            card_id = mapped.get("card_id")
            if not card_id:
                continue
            



            # Deleting data from Google sheet and Json file.
            card_info = cards_by_id.get(card_id)
            if not card_info:
                logger.info("Card %s for sheet id %s missing/archived; setting sheet category to LOST", card_id, sid)
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_category_by_row_index(row_index, "LOST")
                    except Exception as e:
                        logger.exception("Failed setting sheet category to LOST for sid %s: %s", sid, e)
                mappings.pop(sid, None)
                save_state_callback(data_json_path, state)
                continue



            # Category change from trello to Google sheet-

            current_list_id = card_info.get("idList")
            current_list_name = list_id_to_name.get(current_list_id, None)
            if current_list_name:
                current_list_name = current_list_name.lower().strip()
            mapped_category = (mapped.get("category") or "").strip().lower()

            mapped_sheet_cat = TRELLO_TO_SHEET.get(current_list_name) if current_list_name else None
            if mapped_sheet_cat and mapped_sheet_cat != mapped_category:
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_category_by_row_index(row_index, mapped_sheet_cat)
                        mapped["category"] = mapped_sheet_cat
                        save_state_callback(data_json_path, state)
                        logger.info("Updated sheet row %s category -> %s because Trello card %s moved", sid,
                                    mapped_sheet_cat, card_id)
                    except Exception as e:
                        logger.exception("Failed updating sheet category for sid %s: %s", sid, e)

            # Desption of Card- 
            card_desc = card_info.get("desc") or ""
            parsed = trello.parse_desc_to_fields(card_desc)
            trello_card_email = (parsed.get("email") or "").strip()
            trello_card_note = (parsed.get("note") or "").strip()
            trello_card_source = (parsed.get("source") or "").strip()


            trello_card_name = card_info.get("name", "").strip()
            trello_card_name_clean = trello_card_name.split("(", 1)[0].strip()
            trello_card_name = trello_card_name_clean
            mapped_name = (mapped.get("name") or "").strip()


            # Updation of name from trello to card.

            if trello_card_name and trello_card_name != mapped_name:
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_name_by_row_index(row_index, trello_card_name)
                        mapped["name"] = trello_card_name
                        save_state_callback(data_json_path, state)
                        logger.info("Updated sheet row %s name -> %s because Trello card %s title changed", sid,
                                    trello_card_name, card_id)
                    except Exception as e:
                        logger.exception("Failed updating sheet name for sid %s: %s", sid, e)

            # Updation of email from trello to card.

            mapped_email = (mapped.get("email") or "").strip()
            if trello_card_email and trello_card_email != mapped_email:
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_email_by_row_index(row_index, trello_card_email)
                        mapped["email"] = trello_card_email
                        save_state_callback(data_json_path, state)
                        logger.info("Updated sheet row %s email -> %s because Trello card %s desc changed", sid,
                                    trello_card_email, card_id)
                    except Exception as e:
                        logger.exception("Failed updating sheet email for sid %s: %s", sid, e)

            # Updation of note from trello to card.

            mapped_note = (mapped.get("note") or "").strip()
            if trello_card_note and trello_card_note != mapped_note:
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_note_by_row_index(row_index, trello_card_note)
                        mapped["note"] = trello_card_note
                        save_state_callback(data_json_path, state)
                        logger.info("Updated sheet row %s note -> %s because Trello card %s desc changed", sid,
                                    trello_card_note, card_id)
                    except Exception as e:
                        logger.exception("Failed updating sheet note for sid %s: %s", sid, e)

            # Updation of source from trello to card.

            mapped_source = (mapped.get("source") or "").strip()
            if trello_card_source and trello_card_source != mapped_source:
                row_index = sheet.find_row_index_by_id(sid)
                if row_index:
                    try:
                        sheet.update_source_by_row_index(row_index, trello_card_source)
                        mapped["source"] = trello_card_source
                        save_state_callback(data_json_path, state)
                        logger.info("Updated sheet row %s source -> %s because Trello card %s desc changed", sid,
                                    trello_card_source, card_id)
                    except Exception as e:
                        logger.exception("Failed updating sheet source for sid %s: %s", sid, e)

    except Exception as e:
        logger.exception("Error while pulling Trello board/cards: %s", e)